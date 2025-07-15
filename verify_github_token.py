#!/usr/bin/env python3
"""
Verify GitHub token and permissions
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_USERNAME = os.getenv('GITHUB_USERNAME')
TEST_REPO = 'https://github.com/mrlancelot/tb-test'

def check_token():
    """Check if the GitHub token is valid and has proper permissions"""
    
    print("=== GitHub Token Verification ===\n")
    
    if not GITHUB_TOKEN:
        print("❌ ERROR: GITHUB_TOKEN not found in environment")
        return False
    
    print(f"✓ Token found: {GITHUB_TOKEN[:10]}...{GITHUB_TOKEN[-4:]}")
    print(f"✓ Username: {GITHUB_USERNAME}")
    
    # Test 1: Verify token with GitHub API
    print("\n1. Testing token validity...")
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    response = requests.get('https://api.github.com/user', headers=headers)
    
    if response.status_code == 200:
        user_data = response.json()
        print(f"   ✓ Token is valid for user: {user_data.get('login', 'Unknown')}")
        print(f"   ✓ Name: {user_data.get('name', 'Not set')}")
        print(f"   ✓ Email: {user_data.get('email', 'Not set')}")
    else:
        print(f"   ❌ Token validation failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return False
    
    # Test 2: Check token scopes
    print("\n2. Checking token permissions...")
    scopes = response.headers.get('X-OAuth-Scopes', '').split(', ')
    print(f"   Token scopes: {scopes}")
    
    required_scopes = ['repo', 'public_repo']
    has_required_scope = any(scope in scopes for scope in required_scopes)
    
    if has_required_scope or 'repo' in scopes:
        print("   ✓ Token has repository access")
    else:
        print("   ❌ Token missing required scope: 'repo' or 'public_repo'")
        print("   Current scopes:", scopes)
        return False
    
    # Test 3: Check access to specific repository
    print("\n3. Testing repository access...")
    repo_parts = TEST_REPO.replace('https://github.com/', '').strip('/').split('/')
    owner = repo_parts[0]
    repo = repo_parts[1]
    
    repo_response = requests.get(
        f'https://api.github.com/repos/{owner}/{repo}',
        headers=headers
    )
    
    if repo_response.status_code == 200:
        repo_data = repo_response.json()
        print(f"   ✓ Can access repository: {repo_data['full_name']}")
        print(f"   ✓ Private: {repo_data.get('private', False)}")
        print(f"   ✓ Permissions: {repo_data.get('permissions', {})}")
    else:
        print(f"   ❌ Cannot access repository: {repo_response.status_code}")
        print(f"   Error: {repo_response.text}")
        return False
    
    # Test 4: Check if we can create PRs
    print("\n4. Checking PR creation permissions...")
    
    # Check if user can push to repo
    if repo_data.get('permissions', {}).get('push', False):
        print("   ✓ User has push access to repository")
    else:
        print("   ⚠️  User does not have push access")
        print("   Note: You can still create PRs from forked branches")
    
    # Test 5: List existing PRs to verify API access
    print("\n5. Testing PR API access...")
    pr_response = requests.get(
        f'https://api.github.com/repos/{owner}/{repo}/pulls',
        headers=headers,
        params={'state': 'all', 'per_page': 5}
    )
    
    if pr_response.status_code == 200:
        prs = pr_response.json()
        print(f"   ✓ Can access PR API")
        print(f"   ✓ Found {len(prs)} recent PRs")
    else:
        print(f"   ❌ Cannot access PR API: {pr_response.status_code}")
        return False
    
    # Test 6: Check rate limits
    print("\n6. Checking API rate limits...")
    rate_response = requests.get('https://api.github.com/rate_limit', headers=headers)
    
    if rate_response.status_code == 200:
        rate_data = rate_response.json()
        core_rate = rate_data['rate']
        print(f"   ✓ Rate limit: {core_rate['remaining']}/{core_rate['limit']}")
        print(f"   ✓ Resets at: {core_rate['reset']}")
    
    print("\n=== Summary ===")
    print("✓ GitHub token is valid and has necessary permissions")
    print("✓ Can access the target repository")
    print("✓ Can use PR APIs")
    print("\nIf PR creation still fails, the issue might be:")
    print("- Daytona sandbox configuration")
    print("- GitHub CLI authentication in sandbox")
    print("- Network connectivity from sandbox")
    
    return True

if __name__ == "__main__":
    check_token()