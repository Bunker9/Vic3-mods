#!/usr/bin/env python3
"""lib_paths — self-location + ALL external path resolution for THE debug framework (the single I/O-path
lib, vision §Z). Machine paths come from Game-<game>/config-game.toml; auto-resolve (Documents/registry) is
the fallback ONLY when a config key is blank. The game data-dir name is the one game-anchor constant."""
import os
import lib_config   # sibling module in Framework-common (added to sys.path by the caller; hyphenated dir = not a package)

# The ONE game anchor. A future PDX game = a new `Game-<X>/` beside the frameworks (bump or pass --game later).
GAME_DIR = "Game-Victoria3"
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # testbook/v2/tools
GAME_ROOT = os.path.join(TOOLS, GAME_DIR)


def game_config():
    """The per-machine config (abs paths). GITIGNORED; copy from config_game.example.toml on a new machine."""
    return lib_config.load_toml(os.path.join(GAME_ROOT, "config_game.toml"))


def _ensure(d, create):
    if create:
        os.makedirs(d, exist_ok=True)
    return d


def data_dir(mod_name, create=True):
    """ModParse output: Game-<game>/data-<Mod>/ — the idempotent shared artifact both downstreams read."""
    return _ensure(os.path.join(GAME_ROOT, "data-" + mod_name), create)


def run_dir(kind, mod_name, label="", create=True):
    """Per-run output: Game-<game>/<kind>[-<label>]/<Mod>/  (kind = 'log-CURR' or 'save-CURR'). label is an
    OPTIONAL descriptor (e.g. a save name); empty = the bare current-run dir (e.g. log-CURR/<Mod>/). Archiving
    a run = renaming the dir (e.g. log-CURR -> log-<ts>-<branch>) is a user/scrub concern, not done here."""
    name = kind if not label else f"{kind}-{label}"
    return _ensure(os.path.join(GAME_ROOT, name, mod_name), create)


def _documents_dir():
    try:
        import winreg
        key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
            return os.path.expandvars(winreg.QueryValueEx(k, "Personal")[0])
    except Exception:
        return os.path.join(os.path.expanduser("~"), "Documents")


def _vic3_user_subdir(name):
    return os.path.join(_documents_dir(), "Paradox Interactive", "Victoria 3", name)


def resolve_logs_dir(cfg=None, override=None):
    cfg = cfg or {}
    return override or cfg.get("logs_dir") or _vic3_user_subdir("logs")


def resolve_save_games_dir(cfg=None):
    cfg = cfg or {}
    return cfg.get("save_games_dir") or _vic3_user_subdir("save games")


def resolve_save(cfg=None, override=None):
    """The save file: --save override, else newest *.v3 in the save-games dir."""
    if override:
        return override
    sg = resolve_save_games_dir(cfg)
    if not os.path.isdir(sg):
        raise SystemExit(f"save-parse: save-games dir not found: {sg} (set save_games_dir or pass --save)")
    v3 = [os.path.join(sg, f) for f in os.listdir(sg) if f.lower().endswith(".v3")]
    if not v3:
        raise SystemExit(f"save-parse: no *.v3 in {sg} (pass --save <file.v3>)")
    return max(v3, key=os.path.getmtime)


def resolve_mod_path(cfg=None, mod_name=None, override=None):
    """Mod source folder: arg2 override, else config-game.toml [mod_locations].<mod>, else None."""
    cfg = cfg or {}
    return override or (cfg.get("mod_locations", {}) or {}).get(mod_name)
