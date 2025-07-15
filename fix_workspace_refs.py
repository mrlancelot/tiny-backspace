#!/usr/bin/env python3
"""Fix all /workspace references to use self.base_dir"""

import re

# Read the file
with open('api/agent_orchestrator.py', 'r') as f:
    content = f.read()

# Replace all /workspace references with {self.base_dir}
# But we need to be careful with f-strings
replacements = [
    # Simple string replacements
    ('f"ls -la /workspace/{repo}', 'f"ls -la {self.base_dir}/{repo}'),
    ('f"cd /workspace/{repo}', 'f"cd {self.base_dir}/{repo}'),
    ('f"cd /workspace/{repo_name}', 'f"cd {self.base_dir}/{repo_name}'),
    ('f"""You are working in the repository /workspace/{repo}', 'f"""You are working in the repository {self.base_dir}/{repo}'),
    ('"ls -la /workspace/"', 'f"ls -la {self.base_dir}/"'),
    ('f"cd /workspace && git clone', 'f"cd {self.base_dir} && git clone'),
    ('Repository directory not found at /workspace/{repo}', 'Repository directory not found at {self.base_dir}/{repo}'),
]

# Apply replacements
for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        print(f"Replaced: {old} -> {new}")
    else:
        print(f"Not found: {old}")

# Write back
with open('api/agent_orchestrator.py', 'w') as f:
    f.write(content)

print("\nDone! File updated.")