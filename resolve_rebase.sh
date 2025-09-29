#!/bin/bash

# Simple script to resolve rebase conflicts

echo "Resolving git rebase conflicts..."

# Add all files
git add -A

# Continue rebase
git rebase --continue

echo "Rebase resolution complete!"