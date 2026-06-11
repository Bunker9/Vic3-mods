"""
Shared resolver for machine-specific reference paths used by the analysis scripts.

Reads hk-config/config/refpaths.json (gitignored, per-machine); falls back to
refpaths.example.json, then to a built-in default. Keep this next to the scripts that
import it (hk-config/tools/) so `from _refpaths import game_path` works when a script is
run directly (Python puts the script's dir on sys.path).
"""
import os, json

_HERE = os.path.dirname(os.path.abspath(__file__))                 # hk-config/tools
_CFG = os.path.join(os.path.dirname(_HERE), "config")              # hk-config/config
_DEFAULT_GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\game"


def _load():
    for name in ("refpaths.json", "refpaths.example.json"):
        p = os.path.join(_CFG, name)
        if os.path.isfile(p):
            try:
                return json.load(open(p, encoding="utf-8"))
            except Exception:
                pass
    return {}


def game_path():
    """Vic3 vanilla game-files dir (…/Victoria 3/game)."""
    return _load().get("game_files_path") or _DEFAULT_GAME


def vic3_user_dir():
    """Paradox user dir override; '' => caller auto-resolves from Documents."""
    return _load().get("vic3_user_dir") or ""
