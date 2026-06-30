#!/usr/bin/env python3
"""lib_config — read-only TOML config loader (stdlib tomllib, Python 3.11+). Configs are hand-authored;
there is no TOML writer dependency. Used for Game-<game>/config-game.toml + config-naming.toml +
each Framework-*/config-<fw>.toml."""
import os
import tomllib


def load_toml(path):
    """Parse a TOML file -> dict. Missing file => {} (the caller decides whether that is fatal)."""
    if not os.path.exists(path):
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def load_framework_config(framework_dir, filename):
    """Load a Framework-*/config-<fw>.toml that lives beside the framework's scripts."""
    return load_toml(os.path.join(framework_dir, filename))
