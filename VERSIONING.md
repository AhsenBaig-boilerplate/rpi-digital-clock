# Versioning Guide

This project follows [Semantic Versioning 2.0.0](https://semver.org/) and uses Git tags for version management.

## Version Format

- **Release versions**: `v1.3.0`, `v2.0.0`, etc.
- **Development versions**: `v1.3.0+rev76` (tag + commits since tag)

## Current Version

Check the current version:
```bash
git describe --tags
# Example output: v1.3.0-76-gb4f6f93
# Means: 76 commits after v1.3.0, current commit b4f6f93
```

## Semantic Versioning Rules

Given a version number `MAJOR.MINOR.PATCH`:

- **MAJOR**: Breaking changes (e.g., config format changes, API incompatibilities)
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

## Creating a New Release

### 1. Decide the Version Number

Based on changes since last release:
- Bug fixes only → bump PATCH (1.3.0 → 1.3.1)
- New features → bump MINOR (1.3.0 → 1.4.0)
- Breaking changes → bump MAJOR (1.3.0 → 2.0.0)

### 2. Update CHANGELOG

Document changes in `CHANGELOG.md`:
```markdown
## [1.4.0] - 2026-01-08

### Added
- Build tracking and version display in UI
- Comprehensive CI/CD with GitHub metadata tagging

### Fixed
- Seconds display timing issues
```

### 3. Create and Push the Tag

```bash
# Create annotated tag
git tag -a v1.4.0 -m "Release v1.4.0 - Build tracking and version display"

# Push tag to trigger deployment
git push origin v1.4.0
```

### 4. GitHub Actions Automatically

- Detects the tag
- Updates `balena.yml` with version
- Embeds build info with version
- Deploys to Balena
- Tags the Balena release with GitHub metadata

## Quick Release Script

Use this helper script to streamline releases:

```bash
#!/bin/bash
# release.sh - Create a new release

VERSION=$1
if [ -z "$VERSION" ]; then
  echo "Usage: ./release.sh <version>"
  echo "Example: ./release.sh 1.4.0"
  exit 1
fi

# Add v prefix if missing
if [[ ! $VERSION =~ ^v ]]; then
  VERSION="v$VERSION"
fi

# Validate version format
if [[ ! $VERSION =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Error: Invalid version format. Use MAJOR.MINOR.PATCH (e.g., 1.4.0)"
  exit 1
fi

echo "Creating release $VERSION..."

# Ensure we're on main and up to date
git checkout main
git pull

# Create annotated tag
git tag -a $VERSION -m "Release $VERSION"

# Show what will be pushed
echo ""
echo "Tag created: $VERSION"
echo "To push and trigger deployment:"
echo "  git push origin $VERSION"
echo ""
echo "To cancel:"
echo "  git tag -d $VERSION"
```

Save as `scripts/release.sh` and make executable:
```bash
chmod +x scripts/release.sh
```

## Version Display

After deployment, version appears in:

1. **Startup logs**: `Build info: commit=abc1234 ref=main version=v1.4.0 built=2026-01-08T10:10:00Z`
2. **Status bar**: Bottom-right shows `v1.4.0 abc1234`
3. **On-device CLI**: `python3 /app/build_info.py`
4. **Balena dashboard**: Release page shows `git.sha` and `github.run_url` tags

## Development Workflow

Between releases, the workflow automatically generates dev versions:

```
# On tag v1.3.0
→ version: v1.3.0

# 5 commits after v1.3.0
→ version: v1.3.0+rev5

# Next release tag v1.4.0
→ version: v1.4.0
```

This allows you to track exactly which commit is deployed on each device.

## Best Practices

1. **Tag from main branch only** - Ensure stable base
2. **Update CHANGELOG** before tagging
3. **Use annotated tags** (`git tag -a`) for metadata
4. **Test before releasing** - Use `balena push` to test locally first
5. **Follow semver** - Be consistent with version bumps
6. **Document breaking changes** - Clearly note in CHANGELOG and commit message

## Suggested Release Schedule

Current status: **76 commits since v1.3.0** - time for a release!

Recommendations:
- **v1.4.0** (minor) - For new build tracking features
- **v1.3.1** (patch) - If only fixing bugs

## Common Commands

```bash
# Check current version
git describe --tags

# List all tags
git tag -l

# Show commits since last tag
git log $(git describe --tags --abbrev=0)..HEAD --oneline

# Delete a tag (if needed)
git tag -d v1.4.0
git push origin :refs/tags/v1.4.0  # delete remote

# Create release and push
git tag -a v1.4.0 -m "Release v1.4.0"
git push origin v1.4.0
```

## Rollback

If a release has issues:

1. In Balena dashboard, pin devices to previous release
2. Fix the issue
3. Create a new patch release (e.g., v1.4.1)

Never delete published tags - always move forward.
