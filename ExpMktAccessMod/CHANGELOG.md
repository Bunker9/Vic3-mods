# ExpMktAccessMod — Changelog

## v0.5.0-dev (2026-06-12) — redesign (trade centers weren't building)
**Root cause found:** the old `create_building` call passed `reserves = 1` with **no
`level`**, which makes a zero-level shell — so no trade center ever appeared (SOK/PAN).
(Trade centers also need a city + to be off `law_isolationism`; ports need a coastal state.)

Redesign:
- **Economic system → `law_interventionism`** at start (unless already that / laissez-faire) to empower industry + capitalists.
- **`expmkt_industrialist_boost`** modifier, 48 months: industrialists `pol_str_mult = 1.0` + `approval_add = 20` (get them ≥10% and content). Capitalists grow from the new private buildings + interventionism (no clean direct pop-promote exists).
- **Coastal seed** in the best (highest-gdp) coastal state, now with explicit `level`: `building_port` + `building_trade_center` + `building_logging_camp` (wood, the worst early shortage).
- **4-year yearly pulse** (`expmkt.1`) re-runs the coastal seed, so a tag that conquers its first coastal state mid-war still gets a port/trade center. Hard-stops after year 4.

## Runtime flow
`on_game_started_after_lobby` → per expand tag: `expmkt_start_setup` (law + IG modifier + first coastal seed) → schedule `expmkt.1` at +1yr → pulse re-seeds coast yearly through year 4 (idempotent: only builds what's missing).
