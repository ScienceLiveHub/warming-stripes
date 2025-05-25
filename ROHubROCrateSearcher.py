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
    """ROHub searcher using ROHub API methods."""
    
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
    
    def download_rocrate(self, rohub_id: str, output_dir: str):
        """Download a RO-Crate using ROHub API."""
        try:
            print(f"Loading research object: {rohub_id}")
            ro = rohub.ros_export_to_rocrate(identifier=rohub_id, filename = output_dir + "/" + rohub_id, use_format="zip")
            print(f"✓ Successfully loaded RO: {rohub_id}")
            return ro
        except Exception as e:
            print(f"✗ Error loading research object {rohub_id}: {e}")
            return None
    
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
    searcher.authenticate_rohub(username=rohub_user, password=rohub_pwd)
    
    for rohub_id in example_rohub_ids:
        print(f"\n{'='*70}")
        print(f"Analyzing ROHub Research Object: {rohub_id}")
        print(f"{'='*70}")
        
        # Search for workflows
        searcher.download_rocrate(rohub_id, ".")
        

if __name__ == "__main__":
    demonstrate_usage()
