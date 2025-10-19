# Integrator Guide

This guide is for developers building tools that integrate vcs-versioning (like hatch-vcs, custom build backends, or other version management tools).

## Overview

vcs-versioning provides a flexible override system that allows integrators to:

- Use custom environment variable prefixes (e.g., `HATCH_VCS_*` instead of `SETUPTOOLS_SCM_*`)
- Automatically fall back to `VCS_VERSIONING_*` variables for universal configuration
- Apply global overrides once at entry points using a context manager pattern
- Access override values throughout the execution via thread-safe accessor functions

## Quick Start

The simplest way to use the overrides system is with the `GlobalOverrides` context manager:

```python
from vcs_versioning.overrides import GlobalOverrides
from vcs_versioning import infer_version_string

# Use your own prefix
with GlobalOverrides.from_env("HATCH_VCS"):
    # All modules now use HATCH_VCS_* env vars with VCS_VERSIONING_* fallback
    version = infer_version_string(
        dist_name="my-package",
        pyproject_data=pyproject_data,
    )
```

That's it! The context manager:
1. Reads all global override values from environment variables
2. Makes them available to all vcs-versioning internal modules
3. Automatically cleans up when exiting the context

## GlobalOverrides Context Manager

### Basic Usage

```python
from vcs_versioning.overrides import GlobalOverrides

with GlobalOverrides.from_env("YOUR_TOOL"):
    # Your version detection code here
    pass
```

### What Gets Configured

The `GlobalOverrides` context manager reads and applies these configuration values, and automatically configures logging:

| Field | Environment Variables | Default | Description |
|-------|----------------------|---------|-------------|
| `debug` | `{TOOL}_DEBUG`<br>`VCS_VERSIONING_DEBUG` | `False` (WARNING level) | Debug logging level (int) or False |
| `subprocess_timeout` | `{TOOL}_SUBPROCESS_TIMEOUT`<br>`VCS_VERSIONING_SUBPROCESS_TIMEOUT` | `40` | Timeout for subprocess commands in seconds |
| `hg_command` | `{TOOL}_HG_COMMAND`<br>`VCS_VERSIONING_HG_COMMAND` | `"hg"` | Command to use for Mercurial operations |
| `source_date_epoch` | `SOURCE_DATE_EPOCH` | `None` | Unix timestamp for reproducible builds |

**Note:** Logging is automatically configured when entering the `GlobalOverrides` context. The debug level is used to set the log level for all vcs-versioning and setuptools-scm loggers.

### Debug Logging Levels

The `debug` field supports multiple formats:

```bash
# Boolean flag - enables DEBUG level
export HATCH_VCS_DEBUG=1

# Explicit log level (int from logging module)
export HATCH_VCS_DEBUG=10  # DEBUG
export HATCH_VCS_DEBUG=20  # INFO
export HATCH_VCS_DEBUG=30  # WARNING

# Omitted or empty - uses WARNING level (default)
```

### Accessing Override Values

Within the context, you can access override values:

```python
from vcs_versioning.overrides import GlobalOverrides, get_active_overrides

with GlobalOverrides.from_env("HATCH_VCS") as overrides:
    # Direct access
    print(f"Debug level: {overrides.debug}")
    print(f"Timeout: {overrides.subprocess_timeout}")

    # Or via accessor function
    current = get_active_overrides()
    log_level = current.log_level()  # Returns int from logging module
```

### Creating Modified Overrides

Use `from_active()` to create a modified version of the currently active overrides:

```python
from vcs_versioning.overrides import GlobalOverrides
import logging

with GlobalOverrides.from_env("TOOL"):
    # Original context with default settings

    # Create a nested context with modified values
    with GlobalOverrides.from_active(debug=logging.INFO, subprocess_timeout=100):
        # This context has INFO logging and 100s timeout
        # Other fields (hg_command, source_date_epoch, tool) are preserved
        pass
```

This is particularly useful in tests where you want to modify specific overrides without affecting others:

```python
def test_with_custom_timeout():
    # Start with standard test overrides
    with GlobalOverrides.from_active(subprocess_timeout=5):
        # Test with short timeout
        pass
```

### Exporting Overrides

Use `export()` to export overrides to environment variables or pytest monkeypatch:

```python
from vcs_versioning.overrides import GlobalOverrides

# Export to environment dict
overrides = GlobalOverrides.from_env("TOOL", env={"TOOL_DEBUG": "INFO"})
env = {}
overrides.export(env)
# env now contains: {"TOOL_DEBUG": "20", "TOOL_SUBPROCESS_TIMEOUT": "40", ...}

# Export via pytest monkeypatch
def test_subprocess(monkeypatch):
    overrides = GlobalOverrides.from_active(debug=logging.DEBUG)
    overrides.export(monkeypatch)
    # Environment is now set for subprocess calls
    result = subprocess.run(["my-command"], env=os.environ)
```

This is useful when you need to:
- Pass overrides to subprocesses
- Set up environment for integration tests
- Export configuration for external tools

## Automatic Fallback Behavior

The overrides system checks environment variables in this order:

1. **Tool-specific prefix**: `{YOUR_TOOL}_*`
2. **VCS_VERSIONING prefix**: `VCS_VERSIONING_*` (universal fallback)
3. **Default value**: Hard-coded defaults

### Example

```python
with GlobalOverrides.from_env("HATCH_VCS"):
    # Checks in order:
    # 1. HATCH_VCS_DEBUG
    # 2. VCS_VERSIONING_DEBUG
    # 3. Default: False (WARNING level)
    pass
```

This means:
- Users can set `VCS_VERSIONING_DEBUG=1` to enable debug mode for all tools
- Or set `HATCH_VCS_DEBUG=1` to enable it only for hatch-vcs
- The tool-specific setting takes precedence

## Distribution-Specific Overrides

For dist-specific overrides like pretend versions and metadata, use `EnvReader`:

```python
from vcs_versioning.overrides import EnvReader
import os

# Read pretend version for a specific distribution
reader = EnvReader(
    tools_names=("HATCH_VCS", "VCS_VERSIONING"),
    env=os.environ,
    dist_name="my-package",
)
pretend_version = reader.read("PRETEND_VERSION")

# This checks in order:
# 1. HATCH_VCS_PRETEND_VERSION_FOR_MY_PACKAGE
# 2. VCS_VERSIONING_PRETEND_VERSION_FOR_MY_PACKAGE
# 3. HATCH_VCS_PRETEND_VERSION (generic)
# 4. VCS_VERSIONING_PRETEND_VERSION (generic)
```

### Distribution Name Normalization

Distribution names are normalized following PEP 503 semantics, then converted to environment variable format:

```python
"my-package"      → "MY_PACKAGE"
"My.Package_123"  → "MY_PACKAGE_123"
"pkg--name___v2"  → "PKG_NAME_V2"
```

The normalization:
1. Uses `packaging.utils.canonicalize_name()` (PEP 503)
2. Replaces `-` with `_`
3. Converts to uppercase

## EnvReader: Advanced Environment Variable Reading

The `EnvReader` class is the core utility for reading environment variables with automatic fallback between tool prefixes. While `GlobalOverrides` handles the standard global overrides automatically, `EnvReader` is useful when you need to read custom or distribution-specific environment variables.

### Basic Usage

```python
from vcs_versioning.overrides import EnvReader
import os

# Create reader with tool prefix fallback
reader = EnvReader(
    tools_names=("HATCH_VCS", "VCS_VERSIONING"),
    env=os.environ,
)

# Read simple values
debug = reader.read("DEBUG")
timeout = reader.read("SUBPROCESS_TIMEOUT")
custom = reader.read("MY_CUSTOM_VAR")

# Returns None if not found
value = reader.read("NONEXISTENT")  # None
```

### Reading Distribution-Specific Variables

When you provide a `dist_name`, `EnvReader` automatically checks distribution-specific variants first:

```python
reader = EnvReader(
    tools_names=("HATCH_VCS", "VCS_VERSIONING"),
    env=os.environ,
    dist_name="my-package",
)

# Reading "PRETEND_VERSION" checks in order:
# 1. HATCH_VCS_PRETEND_VERSION_FOR_MY_PACKAGE (tool + dist)
# 2. VCS_VERSIONING_PRETEND_VERSION_FOR_MY_PACKAGE (fallback + dist)
# 3. HATCH_VCS_PRETEND_VERSION (tool generic)
# 4. VCS_VERSIONING_PRETEND_VERSION (fallback generic)
pretend = reader.read("PRETEND_VERSION")
```

### Reading TOML Configuration

For structured configuration, use `read_toml()` with TypedDict schemas:

```python
from typing import TypedDict
from vcs_versioning.overrides import EnvReader

class MyConfigSchema(TypedDict, total=False):
    """Schema for configuration validation."""
    local_scheme: str
    version_scheme: str
    timeout: int
    enabled: bool

reader = EnvReader(
    tools_names=("MY_TOOL", "VCS_VERSIONING"),
    env={
        "MY_TOOL_CONFIG": '{local_scheme = "no-local-version", timeout = 120}'
    }
)

# Parse TOML with schema validation
config = reader.read_toml("CONFIG", schema=MyConfigSchema)
# Result: {'local_scheme': 'no-local-version', 'timeout': 120}

# Invalid fields are automatically removed and logged as warnings
```

**TOML Format Support:**

- **Inline maps**: `{key = "value", number = 42}`
- **Full documents**: Multi-line TOML with proper structure
- **Type coercion**: TOML types are preserved (int, bool, datetime, etc.)

### Error Handling and Diagnostics

`EnvReader` provides helpful diagnostics for common mistakes:

#### Alternative Normalizations

If you use a slightly different normalization, you'll get a warning:

```python
reader = EnvReader(
    tools_names=("TOOL",),
    env={"TOOL_VAR_FOR_MY-PACKAGE": "value"},  # Using dashes
    dist_name="my-package"
)

value = reader.read("VAR")
# Warning: Found environment variable 'TOOL_VAR_FOR_MY-PACKAGE' for dist name 'my-package',
# but expected 'TOOL_VAR_FOR_MY_PACKAGE'. Consider using the standard normalized name.
# Returns: "value" (still works!)
```

#### Typo Detection

If you have a typo in the distribution name suffix, you'll get suggestions:

```python
reader = EnvReader(
    tools_names=("TOOL",),
    env={"TOOL_VAR_FOR_MY_PACKGE": "value"},  # Typo: PACKAGE
    dist_name="my-package"
)

value = reader.read("VAR")
# Warning: Environment variable 'TOOL_VAR_FOR_MY_PACKAGE' not found for dist name 'my-package'
# (canonicalized as 'my-package'). Did you mean one of these? ['TOOL_VAR_FOR_MY_PACKGE']
# Returns: None (doesn't match)
```

### Common Patterns

#### Pattern: Reading Pretend Metadata (TOML)

```python
from vcs_versioning._overrides import PretendMetadataDict
from vcs_versioning.overrides import EnvReader

reader = EnvReader(
    tools_names=("MY_TOOL", "VCS_VERSIONING"),
    env=os.environ,
    dist_name="my-package"
)

# Read TOML metadata
metadata = reader.read_toml("PRETEND_METADATA", schema=PretendMetadataDict)
# Example result: {'node': 'g1337beef', 'distance': 4, 'dirty': False}
```

#### Pattern: Reading Configuration Overrides

```python
from vcs_versioning._overrides import ConfigOverridesDict
from vcs_versioning.overrides import EnvReader

reader = EnvReader(
    tools_names=("MY_TOOL", "VCS_VERSIONING"),
    env=os.environ,
    dist_name="my-package"
)

# Read config overrides
overrides = reader.read_toml("OVERRIDES", schema=ConfigOverridesDict)
# Example: {'local_scheme': 'no-local-version', 'version_scheme': 'release-branch-semver'}
```

#### Pattern: Reusing Reader for Multiple Reads

```python
reader = EnvReader(
    tools_names=("MY_TOOL", "VCS_VERSIONING"),
    env=os.environ,
    dist_name="my-package"
)

# Efficient: reuse reader for multiple variables
pretend_version = reader.read("PRETEND_VERSION")
pretend_metadata = reader.read_toml("PRETEND_METADATA", schema=PretendMetadataDict)
config_overrides = reader.read_toml("OVERRIDES", schema=ConfigOverridesDict)
custom_setting = reader.read("CUSTOM_SETTING")
```

### When to Use EnvReader

**Use `EnvReader` when you need to:**

- Read custom environment variables beyond the standard global overrides
- Support distribution-specific configuration
- Parse structured TOML data from environment variables
- Implement your own override system on top of vcs-versioning

**Don't use `EnvReader` for:**

- Standard global overrides (debug, timeout, etc.) - use `GlobalOverrides` instead
- One-time reads - it's designed for efficiency with multiple reads

### EnvReader vs GlobalOverrides

| Feature | `GlobalOverrides` | `EnvReader` |
|---------|------------------|-------------|
| **Purpose** | Manage standard global overrides | Read any custom env vars |
| **Context Manager** | ✅ Yes | ❌ No |
| **Auto-configures logging** | ✅ Yes | ❌ No |
| **Tool fallback** | ✅ Automatic | ✅ Automatic |
| **Dist-specific vars** | ❌ No | ✅ Yes |
| **TOML parsing** | ❌ No | ✅ Yes |
| **Use case** | Entry point setup | Custom config reading |

**Typical usage together:**

```python
from vcs_versioning.overrides import GlobalOverrides, EnvReader
import os

# Apply global overrides
with GlobalOverrides.from_env("MY_TOOL"):
    # Read custom configuration
    reader = EnvReader(
        tools_names=("MY_TOOL", "VCS_VERSIONING"),
        env=os.environ,
        dist_name="my-package"
    )

    custom_config = reader.read_toml("CUSTOM_CONFIG", schema=MySchema)

    # Both global overrides and custom config are now available
    version = detect_version_with_config(custom_config)
```

## Environment Variable Patterns

### Global Override Patterns

| Override | Environment Variables | Example |
|----------|----------------------|---------|
| Debug | `{TOOL}_DEBUG`<br>`VCS_VERSIONING_DEBUG` | `HATCH_VCS_DEBUG=1` |
| Subprocess Timeout | `{TOOL}_SUBPROCESS_TIMEOUT`<br>`VCS_VERSIONING_SUBPROCESS_TIMEOUT` | `HATCH_VCS_SUBPROCESS_TIMEOUT=120` |
| Mercurial Command | `{TOOL}_HG_COMMAND`<br>`VCS_VERSIONING_HG_COMMAND` | `HATCH_VCS_HG_COMMAND=chg` |
| Source Date Epoch | `SOURCE_DATE_EPOCH` | `SOURCE_DATE_EPOCH=1672531200` |

### Distribution-Specific Patterns

| Override | Environment Variables | Example |
|----------|----------------------|---------|
| Pretend Version (specific) | `{TOOL}_PRETEND_VERSION_FOR_{DIST}`<br>`VCS_VERSIONING_PRETEND_VERSION_FOR_{DIST}` | `HATCH_VCS_PRETEND_VERSION_FOR_MY_PKG=1.0.0` |
| Pretend Version (generic) | `{TOOL}_PRETEND_VERSION`<br>`VCS_VERSIONING_PRETEND_VERSION` | `HATCH_VCS_PRETEND_VERSION=1.0.0` |
| Pretend Metadata (specific) | `{TOOL}_PRETEND_METADATA_FOR_{DIST}`<br>`VCS_VERSIONING_PRETEND_METADATA_FOR_{DIST}` | `HATCH_VCS_PRETEND_METADATA_FOR_MY_PKG='{node="g123", distance=4}'` |
| Pretend Metadata (generic) | `{TOOL}_PRETEND_METADATA`<br>`VCS_VERSIONING_PRETEND_METADATA` | `HATCH_VCS_PRETEND_METADATA='{dirty=true}'` |
| Config Overrides (specific) | `{TOOL}_OVERRIDES_FOR_{DIST}`<br>`VCS_VERSIONING_OVERRIDES_FOR_{DIST}` | `HATCH_VCS_OVERRIDES_FOR_MY_PKG='{"local_scheme": "no-local-version"}'` |

## Complete Integration Example

Here's a complete example of integrating vcs-versioning into a build backend:

```python
# my_build_backend.py
from __future__ import annotations

from typing import Any

from vcs_versioning.overrides import GlobalOverrides
from vcs_versioning import infer_version_string


def get_version_for_build(
    dist_name: str,
    pyproject_data: dict[str, Any],
    config_overrides: dict[str, Any] | None = None,
) -> str:
    """Get version for build, using MYBUILD_* environment variables.

    Args:
        dist_name: The distribution/package name (e.g., "my-package")
        pyproject_data: Parsed pyproject.toml data
        config_overrides: Optional configuration overrides

    Returns:
        The computed version string
    """

    # Apply global overrides with custom prefix
    # Logging is automatically configured based on MYBUILD_DEBUG
    with GlobalOverrides.from_env("MYBUILD"):
        # Get version - all subprocess calls and logging respect MYBUILD_* vars
        # dist_name is used for distribution-specific env var lookups
        version = infer_version_string(
            dist_name=dist_name,
            pyproject_data=pyproject_data,
            overrides=config_overrides,
        )

        return version
```

### Usage

The function is called with the distribution name, enabling package-specific overrides:

```python
# Example: Using in a build backend
version = get_version_for_build(
    dist_name="my-package",
    pyproject_data=parsed_pyproject,
    config_overrides={"local_scheme": "no-local-version"},
)
```

Environment variables can override behavior per package:

```bash
# Enable debug logging for this tool only
export MYBUILD_DEBUG=1

# Or use universal VCS_VERSIONING prefix
export VCS_VERSIONING_DEBUG=1

# Override subprocess timeout
export MYBUILD_SUBPROCESS_TIMEOUT=120

# Pretend version for specific package (dist_name="my-package")
export MYBUILD_PRETEND_VERSION_FOR_MY_PACKAGE=1.2.3.dev4

# Or generic pretend version (applies to all packages)
export MYBUILD_PRETEND_VERSION=1.2.3

python -m build
```

## Testing with Custom Prefixes

When testing your integration, you can mock the environment:

```python
import pytest
from vcs_versioning.overrides import GlobalOverrides


def test_with_custom_overrides():
    """Test version detection with custom override prefix."""
    mock_env = {
        "MYTEST_DEBUG": "1",
        "MYTEST_SUBPROCESS_TIMEOUT": "60",
        "SOURCE_DATE_EPOCH": "1672531200",
    }

    with GlobalOverrides.from_env("MYTEST", env=mock_env) as overrides:
        # Verify overrides loaded correctly
        assert overrides.debug != False
        assert overrides.subprocess_timeout == 60
        assert overrides.source_date_epoch == 1672531200

        # Test your version detection logic
        version = detect_version_somehow()
        assert version is not None


def test_with_vcs_versioning_fallback():
    """Test that VCS_VERSIONING prefix works as fallback."""
    mock_env = {
        "VCS_VERSIONING_DEBUG": "1",
        # No MYTEST_ variables
    }

    with GlobalOverrides.from_env("MYTEST", env=mock_env) as overrides:
        # Should use VCS_VERSIONING fallback
        assert overrides.debug != False
```

## Advanced Usage

### Inspecting Active Overrides

```python
from vcs_versioning import get_active_overrides

# Outside any context
overrides = get_active_overrides()
assert overrides is None

# Inside a context
with GlobalOverrides.from_env("HATCH_VCS"):
    overrides = get_active_overrides()
    assert overrides is not None
    assert overrides.tool == "HATCH_VCS"
```

### Using Accessor Functions Directly

```python
from vcs_versioning import (
    get_debug_level,
    get_subprocess_timeout,
    get_hg_command,
    get_source_date_epoch,
)

with GlobalOverrides.from_env("HATCH_VCS"):
    # These functions return values from the active context
    debug = get_debug_level()
    timeout = get_subprocess_timeout()
    hg_cmd = get_hg_command()
    epoch = get_source_date_epoch()
```

Outside a context, these functions fall back to reading `os.environ` directly for backward compatibility.

### Custom Distribution-Specific Overrides

If you need to read custom dist-specific overrides:

```python
from vcs_versioning.overrides import EnvReader
import os

# Read a custom override
reader = EnvReader(
    tools_names=("HATCH_VCS", "VCS_VERSIONING"),
    env=os.environ,
    dist_name="my-package",
)
custom_value = reader.read("MY_CUSTOM_SETTING")

# This checks in order:
# 1. HATCH_VCS_MY_CUSTOM_SETTING_FOR_MY_PACKAGE
# 2. VCS_VERSIONING_MY_CUSTOM_SETTING_FOR_MY_PACKAGE
# 3. HATCH_VCS_MY_CUSTOM_SETTING
# 4. VCS_VERSIONING_MY_CUSTOM_SETTING
```

`EnvReader` includes fuzzy matching and helpful warnings if users specify distribution names incorrectly.

## Best Practices

### 1. Choose Descriptive Prefixes

Use clear, tool-specific prefixes:
- ✅ `HATCH_VCS`, `MYBUILD`, `POETRY_VCS`
- ❌ `TOOL`, `MY`, `X`

### 2. Apply Context at Entry Points

Apply the `GlobalOverrides` context once at your tool's entry point, not repeatedly:

```python
# ✅ Good - apply once at entry point
def main():
    with GlobalOverrides.from_env("HATCH_VCS"):
        # All operations here have access to overrides
        build_project()

# ❌ Bad - repeated context application
def build_project():
    with GlobalOverrides.from_env("HATCH_VCS"):
        get_version()

    with GlobalOverrides.from_env("HATCH_VCS"):  # Wasteful
        write_version_file()
```

### 3. Document Your Environment Variables

Document the environment variables your tool supports, including the fallback behavior:

```markdown
## Environment Variables

- `HATCH_VCS_DEBUG`: Enable debug logging (falls back to `VCS_VERSIONING_DEBUG`)
- `HATCH_VCS_PRETEND_VERSION_FOR_{DIST}`: Override version for distribution
```

### 4. Test Both Prefixes

Test that both your custom prefix and the `VCS_VERSIONING_*` fallback work:

```python
def test_custom_prefix():
    with GlobalOverrides.from_env("MYTOOL", env={"MYTOOL_DEBUG": "1"}):
        ...

def test_fallback_prefix():
    with GlobalOverrides.from_env("MYTOOL", env={"VCS_VERSIONING_DEBUG": "1"}):
        ...
```

### 5. Avoid Nesting Contexts

Don't nest `GlobalOverrides` contexts - it's rarely needed and can be confusing:

```python
# ❌ Avoid this
with GlobalOverrides.from_env("TOOL1"):
    with GlobalOverrides.from_env("TOOL2"):  # Inner context shadows outer
        ...
```

## Thread Safety

The override system uses `contextvars.ContextVar` for thread-local storage, making it safe for concurrent execution:

```python
import concurrent.futures
from vcs_versioning.overrides import GlobalOverrides

def build_package(tool_prefix: str) -> str:
    with GlobalOverrides.from_env(tool_prefix):
        return get_version()

# Each thread has its own override context
with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = [
        executor.submit(build_package, "TOOL1"),
        executor.submit(build_package, "TOOL2"),
    ]
    results = [f.result() for f in futures]
```

## Migration from Direct Environment Reads

If you're migrating code that directly reads environment variables:

```python
# Before
import os

def my_function():
    debug = os.environ.get("SETUPTOOLS_SCM_DEBUG")
    timeout = int(os.environ.get("SETUPTOOLS_SCM_SUBPROCESS_TIMEOUT", "40"))
    # ...

# After
from vcs_versioning.overrides import GlobalOverrides

def main():
    with GlobalOverrides.from_env("MYTOOL"):
        my_function()  # Now uses override context automatically

def my_function():
    # No changes needed! Internal vcs-versioning code uses the context
    pass
```

All internal vcs-versioning modules automatically use the active override context, so you don't need to change their usage.

## See Also

- [Overrides Documentation](overrides.md) - User-facing documentation for setuptools-scm
- [Configuration Guide](config.md) - Configuring vcs-versioning behavior
- [Extending Guide](extending.md) - Creating custom version schemes and plugins

