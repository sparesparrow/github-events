#!/usr/bin/env python3
"""
GitHub Events Monitor API Examples
Run this script to test all API endpoints and generate sample outputs
"""

import requests
import json
import time
from datetime import datetime

def main():
    base_url = "http://localhost:8000"

    print("=" * 60)
    print("GitHub Events Monitor - API Examples")
    print("=" * 60)

    examples = [
        ("Health Check", "/health"),
        ("Event Counts (1 hour)", "/metrics/event-counts?offset_minutes=60"),
        ("VS Code Activity", "/metrics/repository-activity?repo=microsoft/vscode&hours=24"),
        ("Trending Repos", "/metrics/trending?hours=24&limit=5"),
        ("VS Code PR Interval", "/metrics/pr-interval?repo=microsoft/vscode"),
    ]

    results = []

    for name, endpoint in examples:
        print(f"\n{name}:")
        print(f"GET {endpoint}")

        try:
            start_time = time.time()
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            end_time = time.time()

            print(f"Status: {response.status_code}")
            print(f"Response time: {(end_time - start_time)*1000:.1f}ms")

            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)[:200]}...")
                results.append({
                    "name": name,
                    "endpoint": endpoint,
                    "status": response.status_code,
                    "response_time_ms": round((end_time - start_time) * 1000, 1),
                    "data": data
                })
            else:
                print(f"Error: {response.text}")

        except Exception as e:
            print(f"Request failed: {e}")

    # Save results
    with open('api_examples_output.json', 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": results
        }, f, indent=2)

    print(f"\n" + "=" * 60)
    print(f"Completed {len(results)} successful API calls")
    print("Results saved to api_examples_output.json")

if __name__ == "__main__":
    main()
