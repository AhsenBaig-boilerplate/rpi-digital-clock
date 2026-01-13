#!/bin/bash
# Helper script to tag and push without creating duplicate workflow runs
# Usage: ./scripts/tag-and-push.sh v1.4.121 "Commit message"

set -e

VERSION="$1"
MESSAGE="$2"

if [ -z "$VERSION" ] || [ -z "$MESSAGE" ]; then
    echo "Usage: $0 <version> <commit-message>"
    echo "Example: $0 v1.4.121 'Fix bug in sprite cache'"
    exit 1
fi

echo "==================================="
echo "Tag and Push (avoiding duplicates)"
echo "==================================="
echo "Version: $VERSION"
echo "Message: $MESSAGE"
echo ""

# Stage all changes
echo "1. Staging all changes..."
git add -A

# Check if CHANGELOG needs updating
if ! git diff --cached --name-only | grep -q "CHANGELOG.md"; then
    echo "⚠️  Warning: CHANGELOG.md not staged. Did you update it?"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Commit with version in message
echo "2. Creating commit..."
git commit -m "$MESSAGE"

# Tag the commit
echo "3. Tagging commit as $VERSION..."
git tag "$VERSION"

# Push ONLY the tag (not main branch)
echo "4. Pushing tag $VERSION (tag only, not main)..."
git push origin "$VERSION"

echo ""
echo "✅ Done! Workflow will run ONCE for tag push."
echo "📝 Remember to push main branch later if needed:"
echo "   git push origin main"
echo ""
echo "🔍 Monitor workflow at:"
echo "   https://github.com/$(git config remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/actions"
