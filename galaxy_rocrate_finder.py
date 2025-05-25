#!/usr/bin/env python3
"""
RO-Crate Galaxy Workflow Finder for Nanopublications
Focuses on finding Galaxy workflows in RO-Crates from Zenodo and ROHub.
Uses proper APIs and the ROHub Python package.
"""

import requests
import rdflib
from rdflib import Namespace
import json
import re
from urllib.parse import urljoin, urlparse
import sys
from pathlib import Path
import hashlib
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import tempfile
import zipfile
import os
from ROHubROCrateSearcher import ROHubIDExtractor, ROHubROCrateSearcher

# Import nanopub library
from nanopub import Nanopub, NanopubConf

# Import pooch for downloading files
import pooch

# Define namespaces
CITO = Namespace("http://purl.org/spar/cito/")
NP = Namespace("http://www.nanopub.org/nschema#")

class WorkflowInfo:
    """Class to represent a found Galaxy workflow."""
    
    def __init__(self, filename: str, url: str, source: str, **metadata):
        self.filename = filename
        self.url = url
        self.source = source
        self.metadata = metadata
    
    def __repr__(self):
        return f"WorkflowInfo(filename='{self.filename}', source='{self.source}')"
    
    def to_dict(self):
        return {
            'filename': self.filename,
            'url': self.url,
            'source': self.source,
            **self.metadata
        }

def fetch_nanopub(nanopub_uri):
    """Fetch and parse a nanopublication using nanopub-py."""
    try:
        print(f"Fetching nanopub: {nanopub_uri}")
        
        conf = NanopubConf()
        np = Nanopub(source_uri=nanopub_uri, conf=conf)
        
        print(f"✓ Successfully fetched nanopub: {np.source_uri}")
        return np
        
    except Exception as e:
        print(f"✗ Error fetching nanopub: {e}")
        return None

def find_supporting_dois(nanopub):
    """Find DOIs that support the nanopub using cito:obtainsSupportFrom."""
    supporting_dois = []
    
    graphs_to_search = [nanopub.assertion, nanopub.provenance, nanopub.pubinfo]
    
    for graph in graphs_to_search:
        for subj, pred, obj in graph.triples((None, CITO.obtainsSupportFrom, None)):
            doi_str = str(obj)
            if any(doi_str.startswith(prefix) for prefix in ['https://www.doi.org/', 'https://doi.org/', 'http://dx.doi.org/']):
                supporting_dois.append(doi_str)
            elif doi_str.startswith('doi:'):
                supporting_dois.append(f"https://doi.org/{doi_str[4:]}")
    
    return list(set(supporting_dois))

def download_workflow_with_pooch(workflow_info: dict):
    """Download a Galaxy workflow file using pooch."""
    try:
        url = workflow_info["url"]
        filename = workflow_info["filename"]
        print(url)
        print(workflow_info)
        
        print(f"    Downloading {filename}...")
        
        # Download the file directly
        local_path = pooch.retrieve(
            url=url,
            known_hash=None,
            fname=filename,
            path='./downloaded_workflows'
        )

        print(f"File downloaded to: {local_path}")
        return local_path
        
    except Exception as e:
        print(f"    ✗ Error downloading {workflow_info["filename"]}: {e}")
        return None

def validate_galaxy_invocation_workflow(file_path):
    """Validate that the downloaded file is a valid Galaxy workflow invocation."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        invocation_data = json.loads(content)
    except Exception as e:
        print(f"      ⚠ Error validating workflow invocation: {e}")
        return False
        
def validate_galaxy_workflow(file_path):
    """Validate that the downloaded file is a valid Galaxy workflow."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        workflow_data = json.loads(content)
        
        if isinstance(workflow_data, dict):
            # Galaxy workflow indicators
            galaxy_indicators = [
                'format-version', 'a_galaxy_workflow', 'annotation',
                'creator', 'license', 'name', 'steps', 'tags', 'uuid', 'version'
            ]
            
            found_indicators = [key for key in galaxy_indicators if key in workflow_data]
            
            if found_indicators:
                print(f"      ✓ Valid Galaxy workflow")
                if 'name' in workflow_data:
                    print(f"        Name: {workflow_data['name']}")
                if 'steps' in workflow_data:
                    print(f"        Steps: {len(workflow_data['steps'])}")
                return True
            else:
                print(f"      ⚠ JSON file but missing Galaxy workflow indicators")
                return False
        else:
            print(f"      ⚠ File is not a valid JSON object")
            return False
            
    except json.JSONDecodeError:
        print(f"      ⚠ File is not valid JSON")
        return False
    except Exception as e:
        print(f"      ⚠ Error validating workflow: {e}")
        return False

def main():
    """Main function."""
    if len(sys.argv) != 3:
        print("Usage: python rocrate_galaxy_finder.py <nanopub_uri> <output_dir>")
        print("Example: python rocrate_galaxy_finder.py https://w3id.org/np/RAnqaMx3Ri3bR8yY3oiM-BeMJf8LPxidTSqyEpcHyXoLc downloaded_rocrate")
        sys.exit(1)
    
    nanopub_uri = sys.argv[1]
    output_dir = sys.argv[2]

    # Initialize components
    session = requests.Session()
    
    
    # Initialize ROHub
    # Check if HOME environment variable exists
    if 'HOME' in os.environ:
        home_dir = os.environ['HOME']
        print(f"Home directory: {home_dir}")
    else: 
        print("HOME environment variable not found")
    rohub_user = open(home_dir + "/rohub-user").read().rstrip()
    rohub_pwd = open(home_dir + "/rohub-pwd").read().rstrip()

    # Fetch nanopub
    nanopub = fetch_nanopub(nanopub_uri)
    if not nanopub:
        print("Failed to fetch nanopublication")
        return
    
    print(f"\nNanopub Analysis:")
    print(f"  Assertion triples: {len(nanopub.assertion)}")
    print(f"  Provenance triples: {len(nanopub.provenance)}")
    print(f"  Publication info triples: {len(nanopub.pubinfo)}")
    
    # Find supporting DOIs
    supporting_dois = find_supporting_dois(nanopub)
    
    if not supporting_dois:
        print("\n✗ No supporting DOIs found using cito:obtainsSupportFrom")
        return
    
    print(f"\n✓ Found {len(supporting_dois)} supporting DOI(s):")
    for doi in supporting_dois:
        print(f"  • {doi}")
    
    # Search for workflows in each DOI
    for doi in supporting_dois:
        print(f"\nAnalyzing DOI: {doi}")
        
        # Follow DOI redirect
        try:
            response = session.get(doi, timeout=15, allow_redirects=True)
            if response.status_code == 200:
                final_url = response.url
                print(f"  Resolved to: {final_url}")
                
                # Find appropriate searcher - here rohub only
                if 'rohub.org' in final_url:
                    extractor = ROHubIDExtractor()
                    rohub_id = extractor.extract_id(final_url)

                    # Initialize searcher
                    searcher = ROHubROCrateSearcher()
                    searcher.authenticate_rohub(username=rohub_user, password=rohub_pwd)
                    print(f"Analyzing ROHub Research Object: {rohub_id}")
                    # Download RO-Crate
                    searcher.download_rocrate(rohub_id, output_dir)
            else:
                print(f"  ✗ Failed to resolve DOI: {response.status_code}")
                
        except Exception as e:
            print(f"  ✗ Error resolving DOI: {e}")
    

if __name__ == "__main__":
    main()
