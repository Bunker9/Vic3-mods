#!/usr/bin/env python3
"""ext-mod-keywords.py — ModParse extractor: the mod's own keywords/tokens -> data-<Mod>/raw_keywords.csv
(kw_id, kw, kind). Prefix auto-derived (dominant '<short>_' identifier), overridable with --prefix. Records
every identifier with the prefix as a '_'-delimited segment (catches leading 'nous_x' AND wrapped
'modifier_nous_warbonds'). kind = 'def' if 'tok = {' else 'ref'. THE shared join key both downstreams read.
Standalone-runnable; master invokes as subprocess."""
import os
import re
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_io, lib_paths, lib_config, lib_parse

CFG = lib_config.load_framework_config(HERE, "config_modparse.toml")


def main(args):
    mod_path = lib_paths.resolve_mod_path(lib_paths.game_config(), args.mod_name, args.mod_path)
    if not mod_path:
        sys.exit("ext-mod-keywords: no MOD_PATH.")
    files = lib_io.walk_files(mod_path, set(CFG["scan"]["extensions"]))
    filelines = [(rel, lib_io.read_text_lines(ap)) for rel, ap, _fn in files]
    stop = CFG.get("prefix", {}).get("stopwords", [])
    # Prefer the mod's FILENAME convention (<prefix>_<desc>.txt, load-order zz_/NN_ stripped) — far more
    # reliable than identifier frequency, which vanilla effects (add_/building_/region_) pollute. Fall back
    # to identifier frequency only if filenames yield nothing.
    name_toks = [re.sub(r'^(zz_|[0-9]+_)+', '', os.path.splitext(fn)[0]) for _rel, _ap, fn in files]
    idents = [t for _rel, lines in filelines for t in lib_parse.iter_identifiers(lines)]
    prefix = (args.prefix or lib_parse.detect_prefix(name_toks, None, stop)
              or lib_parse.detect_prefix(idents, None, stop))
    if not prefix:
        sys.exit("ext-mod-keywords: could not derive a keyword prefix; pass --prefix.")
    seen = {}   # kw -> kind ('def' wins over 'ref')
    for _rel, lines in filelines:
        for line in lines:
            for kw in lib_parse.iter_identifiers([line]):
                if prefix not in kw.split("_"):
                    continue
                is_def = bool(re.search(re.escape(kw) + r"\s*=\s*\{", line))
                if kw not in seen or is_def:
                    seen[kw] = "def" if is_def else seen.get(kw, "ref")
    rows = [[i, kw, kind] for i, (kw, kind) in enumerate(sorted(seen.items()), 1)]
    out = os.path.join(lib_paths.data_dir(args.mod_name), CFG["outputs"]["keywords"])
    lib_io.write_csv(out, ["kw_id", "kw", "kind"], rows)
    print(f"  [keywords] {len(rows)} (prefix '{prefix}_') -> {out}")
    return out


if __name__ == "__main__":
    main(lib_args.parse_args("ModParse: extract mod keywords/tokens.", mod_path=True))
