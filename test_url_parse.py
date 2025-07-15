#!/usr/bin/env python3
"""Test URL parsing"""

import re

def _parse_github_url(url: str):
    """Parse GitHub URL to extract owner and repo"""
    # Handle both HTTPS and SSH formats
    url = url.strip()
    
    # HTTPS format: https://github.com/owner/repo or https://github.com/owner/repo.git
    https_match = re.match(r'https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$', url)
    if https_match:
        return {
            'owner': https_match.group(1),
            'repo': https_match.group(2)
        }
    
    # SSH format: git@github.com:owner/repo.git
    ssh_match = re.match(r'git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$', url)
    if ssh_match:
        return {
            'owner': ssh_match.group(1),
            'repo': ssh_match.group(2)
        }
    
    # If neither format matches, provide helpful error
    raise ValueError(f"Invalid GitHub URL format: '{url}'. Expected formats: https://github.com/owner/repo or git@github.com:owner/repo.git")

# Test with the actual URL
test_url = "https://github.com/mrlancelot/tb-test"
result = _parse_github_url(test_url)
print(f"URL: {test_url}")
print(f"Parsed: {result}")
print(f"Owner: {result['owner']}")
print(f"Repo: {result['repo']}")