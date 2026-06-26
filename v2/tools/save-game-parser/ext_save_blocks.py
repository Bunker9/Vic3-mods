#!/usr/bin/env python3
r"""ext_save_blocks.py — stage 1a: RAW per-manager extractors from a Vic3 save.

ONE streaming pass over the decompressed save. For each manager database we care about, dump every
record as a flat row into its own `raw_*.csv`. These raw files are the REUSABLE substrate — the join /
analysis (`aggr_state_census.py`) reads ONLY these CSVs and the variable findings, never the 11M-line
save again (DEV-RULES "modular sub-scripts": thin subs, one job each, no re-parsing).

Outputs (in save-game-parser/<MOD_NAME>/):
  raw_buildings.csv   one row per building   : id, building, levels, last_updated_level, active, state, subsidized, establishment_date
  raw_states.csv      one row per state inst. : id, country, capital, incorporation, region, province
  raw_countries.csv   one row per country     : id, definition (tag), tag, country_type

The join bridges building.state -> states.country -> countries.definition (owner tag).
"""
import re
import lib_saveparse as L

_OPENER = re.compile(r'^\s*([\w:.\-]+)=\{')
_SCALAR = re.compile(r'^\s*([A-Za-z_]\w*)=("?[^"{}\n]*"?)\s*$')

# manager database -> (output basename, scalar fields to capture at the record's top level)
TARGETS = {
    'building_manager': ('raw_buildings',
                         ['building', 'levels', 'last_updated_level', 'active', 'state',
                          'subsidized', 'establishment_date']),
    'states':           ('raw_states',
                         ['country', 'capital', 'incorporation', 'region', 'province']),
    'country_manager':  ('raw_countries',
                         ['definition', 'tag', 'country_type']),
    'state_region_manager': ('raw_state_regions',
                         ['template']),
}


def main(args):
    save = L.resolve_save(args.save)
    print(f"  ext: scan {save}")
    rows = {name: [] for (name, _f) in TARGETS.values()}
    named = []          # (open_depth, key) for named-block openers -> structural breadcrumb
    depth = 0
    rec = None          # (mgr, outname, fields, id, data_dict, rec_depth)

    for line in L.iter_save_lines(save):
        # 1) collect a scalar into the active record
        if rec is not None:
            m = _SCALAR.match(line)
            if m and m.group(1) in rec[2] and m.group(1) not in rec[4]:
                rec[4][m.group(1)] = m.group(2).strip().strip('"')

        # 2) structural update: push named openers
        opener = _OPENER.match(line)
        opens, closes = line.count('{'), line.count('}')
        if opener and opens > closes:
            named.append((depth, opener.group(1)))
            if rec is None and len(named) >= 3:
                gp, par, idk = named[-3][1], named[-2][1], named[-1][1]
                if gp in TARGETS and par == 'database' and re.fullmatch(r'-?\d+', idk):
                    outname, fields = TARGETS[gp]
                    rec = (gp, outname, fields, idk, {}, depth)
        depth += opens - closes
        if depth < 0:
            depth = 0

        # 3) pop closed blocks; emit a record when ITS id-block closes
        while named and named[-1][0] >= depth:
            popped = named.pop()
            if rec is not None and popped[0] == rec[5] and popped[1] == rec[3]:
                _mgr, outname, fields, idk, data, _d = rec
                rows[outname].append([idk] + [data.get(f, '') for f in fields])
                rec = None

    for _gp, (outname, fields) in TARGETS.items():
        L.write_csv(L.out_path(args.mod_name, outname + '.csv'), ['id'] + fields, rows[outname])
        print(f"  -> {outname}.csv: {len(rows[outname])} rows")
    return rows


if __name__ == "__main__":
    main(L.parse_args("Raw per-manager block extractor from a Vic3 save (stage 1a)."))
