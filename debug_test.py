#!/usr/bin/env python3
"""Debug test to see the exact PR creation error"""

import re

def test_url_parsing():
    """Test the URL parsing regex"""
    test_urls = [
        "https://github.com/mrlancelot/tb-test",
        "https://github.com/mrlancelot/tb-test.git",
        "https://github.com/mrlancelot/tb-test/",
        "git@github.com:mrlancelot/tb-test.git",
        "https://github.com/mrlancelot/tb-test\n",  # With newline
        "https://github.com/mrlancelot/tb-test.git\n",  # With newline
    ]
    
    pattern = r'https://github\.com/([^/]+)/([^/]+)(?:\.git)?/?$'
    
    print("Testing URL parsing pattern:")
    print(f"Pattern: {pattern}\n")
    
    for url in test_urls:
        print(f"URL: {repr(url)}")
        match = re.match(pattern, url.strip())
        if match:
            print(f"  ✅ Match: owner={match.group(1)}, repo={match.group(2)}")
        else:
            print(f"  ❌ No match")
        print()

if __name__ == "__main__":
    test_url_parsing()