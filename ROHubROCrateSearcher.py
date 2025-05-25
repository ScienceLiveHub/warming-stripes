#!/usr/bin/env python3
"""
Improved ROHub RO-Crate resource listing based on ROHub API documentation
"""

import re
import os
import rohub
import pandas as pd
from typing import List, Dict, Any, Optional

class ROHubIDExtractor:
    """Extract ROHub IDs from various URL formats."""

    def __init__(self):
        # UUID pattern (ROHub IDs are typically UUIDs)
        self.uuid_pattern = r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'

        # Different ROHub URL patterns
        self.patterns = [
            # Standard ROHub URLs
            rf'rohub\.org/([a-f0-9]{{8}}-[a-f0-9]{{4}}-[a-f0-9]{{4}}-[a-f0-9]{{4}}-[a-f0-9]{{12}})',

            # W3ID redirect URLs
            rf'w3id\.org/ro-id/([a-f0-9]{{8}}-[a-f0-9]{{4}}-[a-f0-9]{{4}}-[a-f0-9]{{4}}-[a-f0-9]{{12}})',

            # API URLs
            rf'api\.rohub\.org/(?:api/)?ros/([a-f0-9]{{8}}-[a-f0-9]{{4}}-[a-f0-9]{{4}}-[a-f0-9]{{4}}-[a-f0-9]{{12}})',

            # DOI URLs that might redirect to ROHub
            rf'doi\.org/.*rohub.*?([a-f0-9]{{8}}-[a-f0-9]{{4}}-[a-f0-9]{{4}}-[a-f0-9]{{4}}-[a-f0-9]{{12}})',
        ]
    def extract_id(self, url: str) -> Optional[str]:
        """
        Extract ROHub ID from URL using multiple methods.

        Args:
            url: ROHub URL in various formats

        Returns:
            ROHub ID (UUID) as string, or None if not found
        """
        if not url:
            return None

        # Try regex patterns
        rohub_id = self._extract_with_regex(url)
        if rohub_id:
            return rohub_id

        return None

    def _extract_with_regex(self, url: str) -> Optional[str]:
        """Extract using predefined regex patterns."""
        for pattern in self.patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

class ROHubROCrateSearcher:
    """Improved ROHub searcher using proper ROHub API methods."""
    
    def __init__(self):
        self.name = "ROHub"
    
    def authenticate_rohub(self, username: str = None, password: str = None):
        """Authenticate with ROHub if credentials are provided."""
        try:
            if username and password:
                rohub.login(username=username, password=password)
                print("✓ Successfully authenticated with ROHub")
            else:
                print("Note: No ROHub credentials provided. Only public ROs will be accessible.")
        except Exception as e:
            print(f"Warning: ROHub authentication failed: {e}")
    
    def load_research_object(self, rohub_id: str):
        """Load a research object using ROHub API."""
        try:
            print(f"Loading research object: {rohub_id}")
            ro = rohub.ros_load(identifier=rohub_id)
            print(f"✓ Successfully loaded RO: {ro.title}")
            return ro
        except Exception as e:
            print(f"✗ Error loading research object {rohub_id}: {e}")
            return None
    
    def list_all_resources(self, ro) -> pd.DataFrame:
        """List all resources in the research object."""
        try:
            print("Fetching resource list...")
            resources_df = ro.list_resources()
            print(f"✓ Found {len(resources_df)} resources")
            
            # Display basic info about the resources
            if len(resources_df) > 0:
                print("\nResource Overview:")
                for idx, row in resources_df.iterrows():
                    name = row.get('name', row.get('filename', 'unnamed'))
                    resource_type = row.get('type', 'unknown')
                    size = row.get('size', 'unknown')
                    print(f"  [{idx}] {name} (type: {resource_type}, size: {size})")
            
            return resources_df
            
        except Exception as e:
            print(f"✗ Error listing resources: {e}")
            return pd.DataFrame()
    
    def find_galaxy_workflows_in_resources(self, resources_df: pd.DataFrame) -> List[Dict]:
        """Find Galaxy workflow files in the resource list."""
        workflows = []
        
        print("\nLooking for Galaxy workflow files...")
        
        for idx, row in resources_df.iterrows():
            resource_name = row.get('name', row.get('filename', ''))
            resource_type = row.get('type', '')
            
            # Look for .ga files (Galaxy workflow files)
            if resource_name.endswith('.ga') and resource_type == "Computational workflow":
                workflow_info = {
                    'filename': resource_name,
                    'resource_id': row.get('identifier', row.get('uri', '')),
                    'download_url': row.get('url', row.get('download_url', '')),
                    'size': row.get('size'),
                    'type': resource_type,
                    'source': 'rohub-direct',
                    'resource_row': row.to_dict()
                }
                workflows.append(workflow_info)
                print(f"✓ Found Galaxy workflow: {resource_name}")
        
        return workflows
    
    def search_workflows_in_ro(self, rohub_id: str, ro=None) -> List[Dict]:
        """Complete workflow search in a ROHub research object."""
        all_workflows = []
        
        # Load research object if not provided
        if ro is None:
            ro = self.load_research_object(rohub_id)
            if not ro:
                return all_workflows
        
        # List all resources
        resources_df = self.list_all_resources(ro)
        if len(resources_df) == 0:
            print("No resources found in research object")
            return all_workflows
        
        # Find direct Galaxy workflow files
        direct_workflows = self.find_galaxy_workflows_in_resources(resources_df)
        
        # Merge and deduplicate workflows
        # Add direct workflows that weren't found via RO-Crate
        for direct_wf in direct_workflows:
            if not any(wf['filename'] == direct_wf['filename'] for wf in all_workflows):
                all_workflows.append(direct_wf)
        
        return all_workflows

    def get_workflows_download_info(self, rohub_id: str, workflows: List[Dict], ro=None) -> List[Dict]:
        """get URLs for workflows already found in a ROHub research object."""
        download_urls = []
    
        # Load research object if not provided
        if ro is None:
            ro = self.load_research_object(rohub_id)
            if not ro:
                return download_urls

        for workflow_info in workflows:
            url = workflow_info["download_url"]
            filename = workflow_info["filename"]
            if url is None:
                # search in resource_row
                url = workflow_info["resource_row"]["download_url"]
                download_urls.append({"filename": filename, "url": url})
        return download_urls

def demonstrate_usage():
    """Demonstrate how to use the improved ROHub searcher."""
    
    # Example ROHub IDs (replace with actual ones)
    example_rohub_ids = [
        "d5430aa5-7a8b-44fe-8d21-6a7c80ac36d4",  # From the documentation example
        # Add more ROHub IDs here
    ]
    
    # Initialize searcher
    searcher = ROHubROCrateSearcher()
    
    # Optional: Authenticate (uncomment and provide credentials if needed)
    # Check if HOME environment variable exists
    if 'HOME' in os.environ:
        home_dir = os.environ['HOME']
        print(f"Home directory: {home_dir}")
    else:
        print("HOME environment variable not found")
    rohub_user = open(home_dir + "/rohub-user").read().rstrip()
    rohub_pwd = open(home_dir + "/rohub-pwd").read().rstrip()
    #rohub.login(username=rohub_user, password=rohub_pwd)
    searcher.authenticate_rohub(username=rohub_user, password=rohub_pwd)
    
    for rohub_id in example_rohub_ids:
        print(f"\n{'='*70}")
        print(f"Analyzing ROHub Research Object: {rohub_id}")
        print(f"{'='*70}")
        
        # Search for workflows
        workflows = searcher.search_workflows_in_ro(rohub_id)
        
        # Display results
        if workflows:
            print(f"\n✓ Found {len(workflows)} Galaxy workflow(s):")
            for i, wf in enumerate(workflows, 1):
                print(f"\n{i}. {wf['filename']}")
                print(f"   Source: {wf['source']}")
                if wf.get('description'):
                    print(f"   Description: {wf['description']}")
                if wf.get('contentSize'):
                    print(f"   Size: {wf['contentSize']} bytes")
                if wf.get('confirmed_galaxy'):
                    print(f"   ✓ Confirmed Galaxy workflow")
        else:
            print("\n✗ No Galaxy workflows found")

if __name__ == "__main__":
    demonstrate_usage()
