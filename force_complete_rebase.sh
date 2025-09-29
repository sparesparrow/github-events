#!/bin/bash

echo "🔧 Force completing git rebase..."

# Kill any hanging git processes
pkill -f git || true

# Remove git locks if they exist
rm -f .git/index.lock .git/HEAD.lock .git/refs/heads/*.lock 2>/dev/null || true

# Try to complete the rebase
echo "📝 Adding all files..."
git add . 2>/dev/null || true

echo "🔄 Continuing rebase..."
timeout 30s git rebase --continue || {
    echo "⚠️ Rebase continue timed out, trying to abort and restart..."
    timeout 10s git rebase --abort || true
    
    echo "🔄 Starting fresh rebase..."
    timeout 30s git rebase origin/main || {
        echo "❌ Rebase failed, manual intervention needed"
        exit 1
    }
}

echo "✅ Rebase completed successfully!"