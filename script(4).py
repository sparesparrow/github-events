# Let's create a comprehensive GitHub Events monitoring solution
# First, let's analyze the structure of the provided GitHub Events data

import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Sample data from the attachment to understand the structure
sample_event_data = '''
{
    "id": "38990681048",
    "type": "PullRequestEvent", 
    "actor": {
        "id": 158077861,
        "login": "gus-opentensor",
        "display_login": "gus-opentensor"
    },
    "repo": {
        "id": 283347912,
        "name": "opentensor/bittensor"
    },
    "payload": {
        "action": "closed",
        "number": 1969,
        "pull_request": {
            "state": "closed",
            "merged": false
        }
    },
    "public": true,
    "created_at": "2024-06-04T15:55:23Z"
}
'''

# Parse the sample to understand structure
sample = json.loads(sample_event_data)
print("Sample GitHub Event Structure:")
print(f"ID: {sample['id']}")
print(f"Type: {sample['type']}")
print(f"Repository: {sample['repo']['name']}")
print(f"Created At: {sample['created_at']}")
print(f"Payload Action: {sample['payload'].get('action', 'N/A')}")
print()

# Let's create the directory structure
import os
os.makedirs("github_events_monitor", exist_ok=True)
os.makedirs("github_events_monitor/tests", exist_ok=True)
os.makedirs("github_events_monitor/tests/unit", exist_ok=True)
os.makedirs("github_events_monitor/tests/integration", exist_ok=True)

print("Created directory structure:")
print("- github_events_monitor/")
print("  - tests/")
print("    - unit/")
print("    - integration/")