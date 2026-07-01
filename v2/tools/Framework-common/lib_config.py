#!/usr/bin/env python3
"""lib_config — read-only TOML config loader (stdlib tomllib, Python 3.11+). Configs are hand-authored;
there is no TOML writer dependency. Used for Framework-common/config_game.toml + config_naming.toml +
each Framework-*/config_<fw>.toml."""
import os
import tomllib


def load_toml(path):
    """Parse a TOML file -> dict. Missing file => {} (the caller decides whether that is fatal).

    Windows-path tolerance: TOML basic (double-quoted) strings treat `\\` as an escape, so a pasted Windows
    path like "C:\\Users\\..." (or a OneDrive save path) is a TOMLDecodeError. If strict parse fails, retry
    once with single backslashes normalized to forward slashes (valid + equivalent on Windows). So a per-machine
    config may use native backslash paths OR forward slashes OR TOML literal (single-quoted) strings."""
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8-sig") as f:
        text = f.read()
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return tomllib.loads(text.replace("\\", "/"))


def load_framework_config(framework_dir, filename):
    """Load a Framework-*/config-<fw>.toml that lives beside the framework's scripts."""
    return load_toml(os.path.join(framework_dir, filename))
