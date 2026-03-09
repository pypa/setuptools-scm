# Changelog Fragments

This directory contains changelog fragments that will be assembled into the CHANGELOG.md file during release.

## Fragment Types

- **feature**: New features or enhancements
- **bugfix**: Bug fixes
- **deprecation**: Deprecation warnings
- **removal**: Removed features (breaking changes)
- **doc**: Documentation improvements
- **misc**: Internal changes, refactoring, etc.

## Naming Convention

Fragments should be named: `{issue_number}.{type}.md`

Examples:
- `123.feature.md` - New feature related to issue #123
- `456.bugfix.md` - Bug fix for issue #456
- `789.doc.md` - Documentation update for issue #789

## Content

Each fragment should contain a brief description of the change:

```markdown
Add support for custom version schemes via plugin system
```

Do not include issue numbers in the content - they will be added automatically.

