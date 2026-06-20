# BDD — ExpFightMod

One Y/N question **per feature**. Fill the **Y/N** column with your in-game observation;
`Exp` = expected answer (the report asserts Answer == Exp). Build label is in the section
header (auto-read from the versiontest stamp).

War-footing granted at game start (`on_game_started_after_lobby` → `expfight_startup`).
Expand tags: MEX BRZ PER PAN DEI SOK DAI NEP CLM ARG SIA MOR OMA SHW SAF.
Long-war (strong `expfight_warboost`, 120mo): PAN DEI SOK SHW DAI NEP CLM OMA ARG SIA MOR.
Short (light `expfight_warbump`, 60mo): MEX BRZ PER SAF.

| # | Feature | Question | Exp | Y/N | Comment |
|---|---------|----------|-----|-----|---------|
| 1 | Startup grant | Did every expand tag get a war-footing modifier on game start? | Y | | check a few tags' modifier list |
| 2 | Strong vs light split | Do long-war tags (ARG/MOR/OMA…) show `expfight_warboost`, short tags (MEX/BRZ/PER/SAF) `expfight_warbump`? | Y | | modifier tooltip |
| 3 | Flat combat edge | Does warboost give +30 unit offense / +50 unit defense (visible flat values)? | Y | | the _mult values were invisible before |
| 4 | Win-the-war effect | Do ARG and MOR actually WIN their early wars with the boost? | Y | | the reason offense went 10→30 |
| 5 | Mobility / upkeep | Does warboost give ~4× army movement+mobilization and -50% military goods cost? | Y | | armies reach the front fast |
| 6 | Armed-forces happy | Does the modifier raise armed-forces political strength + approval (so bonuses get used)? | Y | | IG panel |
| 7 | Durations | Does warboost last 120 months and warbump 60 months, then expire? | Y | | timed modifier countdown |
| 8 | No naval | Are there NO naval bonuses (by design, to avoid AI micro-fleets)? | Y | | |
| 9 | Clean log | Is error.log free of expfight.* errors? | Y | | runs once at lobby, before any annex |
