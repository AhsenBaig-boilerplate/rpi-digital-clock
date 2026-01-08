#!/bin/bash
# release.sh - Create a new version release for the project
# Usage: ./scripts/release.sh <version>
# Example: ./scripts/release.sh 1.4.0

set -e

VERSION=$1
if [ -z "$VERSION" ]; then
  echo "Usage: $0 <version>"
  echo "Example: $0 1.4.0"
  echo ""
  echo "Current version:"
  git describe --tags 2>/dev/null || echo "No tags found"
  echo ""
  echo "Commits since last tag:"
  git log $(git describe --tags --abbrev=0 2>/dev/null || echo "HEAD")..HEAD --oneline | wc -l
  exit 1
fi

# Add v prefix if missing
if [[ ! $VERSION =~ ^v ]]; then
  VERSION="v$VERSION"
fi

# Validate version format
if [[ ! $VERSION =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "❌ Error: Invalid version format. Use MAJOR.MINOR.PATCH (e.g., 1.4.0)"
  exit 1
fi

# Check if tag already exists
if git rev-parse "$VERSION" >/dev/null 2>&1; then
  echo "❌ Error: Tag $VERSION already exists!"
  exit 1
fi

# Ensure we're in repo root
cd "$(git rev-parse --show-toplevel)"

# Ensure working tree is clean
if [[ -n $(git status -s) ]]; then
  echo "⚠️  Warning: Working tree has uncommitted changes"
  git status -s
  read -p "Continue anyway? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

# Show what's changed since last tag
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
if [ -n "$LAST_TAG" ]; then
  echo ""
  echo "📝 Changes since $LAST_TAG:"
  echo "================================"
  git log $LAST_TAG..HEAD --oneline --pretty=format:"  - %s" | head -20
  echo ""
  echo "================================"
  COMMIT_COUNT=$(git log $LAST_TAG..HEAD --oneline | wc -l)
  echo "Total commits: $COMMIT_COUNT"
else
  echo "📝 This will be the first tag"
fi

echo ""
echo "🏷️  Creating release: $VERSION"
echo ""
read -p "Enter release notes (or press Enter for default): " NOTES

if [ -z "$NOTES" ]; then
  NOTES="Release $VERSION"
fi

# Create annotated tag
git tag -a "$VERSION" -m "$NOTES"

echo ""
echo "✅ Tag created: $VERSION"
echo ""
echo "Next steps:"
echo "  1. Review: git show $VERSION"
echo "  2. Push tag to trigger deployment:"
echo "     git push origin $VERSION"
echo ""
echo "  Or to cancel:"
echo "     git tag -d $VERSION"
