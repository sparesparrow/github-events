#!/usr/bin/env python3

import os
import glob

def check_for_conflicts():
    """Check for git conflict markers in all files."""
    conflict_markers = ['<<<<<<< HEAD', '=======', '>>>>>>> ']
    
    # Find all text files
    files_to_check = []
    for ext in ['*.py', '*.md', '*.txt', '*.yml', '*.yaml', '*.json', '*.sh']:
        files_to_check.extend(glob.glob(f'**/{ext}', recursive=True))
    
    conflicts_found = []
    
    for file_path in files_to_check:
        if '.git' in file_path:
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for marker in conflict_markers:
                if marker in content:
                    conflicts_found.append(f"{file_path}: {marker}")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    
    return conflicts_found

if __name__ == "__main__":
    conflicts = check_for_conflicts()
    
    if conflicts:
        print("❌ Conflicts found:")
        for conflict in conflicts:
            print(f"  {conflict}")
    else:
        print("✅ No conflicts found - all resolved!")
        print("\nFiles are ready for git operations.")