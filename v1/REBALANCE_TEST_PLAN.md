# Rebalance Test Plan (2026-06-15)

Test script for verifying all 7 rebalance tasks (A-G) in-game.

## Quick Start

### 1. Pre-Game Checklist
```bash
cd testbook/v1/testkit/checks
python pretest_checklist.py
```
Verifies all rebalance files are present, events updated, triggers patched.

### 2. Clear Logs
```powershell
# Windows
cd hk-config/tools
.\clear-vic3-logs.ps1
```

### 3. Launch Game
- Open Victoria 3 launcher, select all mods
- Play as **Punjab (PAN)** for best test visibility
- Play through **1851.12.31** (to see subject annexation window close)

### 4. Post-Game Verification

#### A. Run rebalance_verify.py
```bash
python testbook/v1/testkit/checks/rebalance_verify.py "path/to/error.log"
```
Scans error log for mdp.3, soft-remove, East Africa issues.

#### B. Fill in testbook BDD
Open `testbook/MyDiploPlayMod/bdd.md`, answer Y/N for each question.
Run test harness to validate:
```bash
python testbook/v1/testkit/run_test.py
```
Report is generated in `testbook/MyDiploPlayMod/report.html`.

#### C. Fill in Observations
Open `testbook/MyDiploPlayMod/observe.md`, note what you saw at each year.

---

## Task-by-Task Observations

### Task A: East Africa Override
| Year | Check | Mod file | Notes |
|------|-------|----------|-------|
| 1836.1.1 | SHW cotton in STATE_OROMIA | Top40EcoBoostMod | Building tab → SHW → STATE_OROMIA |
| 1836.1.1 | EGY cotton in STATE_ERITREA | Top40EcoBoostMod | Building tab → EGY → STATE_ERITREA |

**Expected:** 2 cotton_plantation buildings (1 level each), one per nation.

### Task B: Soft-Remove (BIC/PRU/EGY/SAR/SWE)
| Year | Check | Expected | Notes |
|------|-------|----------|-------|
| 1836.1.1 | BIC receives day-1 war | YES | BIC vs SAR (or similar) visible in war log |
| 1836.6.1 | BIC does NOT start 2nd war | YES | mdp.1 disabled for BIC; only day-1 war active |
| 1836.1.1 | BIC infamy-decay modifier = 36mo | YES | Check modifier tooltip (was 120mo) |
| 1836-1846 | Other expanders (MEX/BRZ) still warring | YES | mdp.1 fires for MEX/BRZ/etc; see multiple wars |
| 1846+ | MEX/BRZ wars stop (window closes) | YES | game_date >= 1846.1.1 blocks mdp.1 |

**Expected:** BIC locked in 1 day-1 war; other expanders continue until 1846.

### Task C & D: Parked TODO
Not tested this round.

### Task E: BetterPopPromoMod Audit
Not tested (mod not yet set up in separate worktree).

### Task F: Oil/Rubber Seeding
| Year | Check | Count | States |
|------|-------|-------|--------|
| 1836.1.1 | BRZ rubber plantations | 5 | SAO_PAULO, RIO_DE_JANEIRO, MINAS_GERAIS, BAHIA, PARANA |
| 1836.1.1 | OMA oil rigs | 5 | OMAN, ZANZIBAR, ABU_DHABI, LARISTAN, KENYA |

**Expected:** 1 building per state, no duplicates, all owned by respective nations.

### Task G: Subject Annexation (mdp.3)
| Year | Check | Expected | Notes |
|------|-------|----------|-------|
| 1846.1.1 | mdp.3 fires (any country with subjects) | YES | Watch for annexation war declarations |
| 1846-1851 | Powers annex weakest subjects | YES | Should see multiple annexations if subjects exist |
| 1846-1851 | Requires 6+ months at peace | YES | No annexation if in active war/diplo-play |
| 1851.12.31+ | mdp.3 stops firing | YES | After window closes, no more annexations |

**Expected:** Subjects gradually annexed during the 5-year window (1846-1851).

### Truces (OMA↔NEJ)
| Year | Check | Expected | Notes |
|------|-------|----------|-------|
| 1836.1.1 | OMA↔NEJ truce exists | YES (4yr) | Diplomacy tab → view OMA/NEJ bidirectional truce |
| 1836.1.1 | Inter-expander truces absent | YES | No BIC↔PRU, PRU↔SWE, etc | (removed in rebalance) |

**Expected:** 1 truce (OMA↔NEJ), none others (except vanilla).

---

## Test Checklist (for user to complete)

### Pre-Game
- [ ] Run `pretest_checklist.py` — all pass?
- [ ] Clear error.log
- [ ] versiontestMod stamped and in mod load order?

### In-Game (Year-by-Year)
- [ ] 1836.1.1: BIC/SHW/EGY/BRZ/OMA buildings present? (BDD #1-16)
- [ ] 1836.1.1: Soft-remove tags (BIC/PRU/EGY/SAR/SWE) show correct infamy modifier? (BDD #12)
- [ ] ~1836-1846: Other expanders still warring monthly? (BDD #11)
- [ ] ~1846.1.1: mdp.3 fires (see annexation attempts)? (BDD #17)
- [ ] 1846-1851: Subject annexations happen? (BDD #17-19)
- [ ] 1851.12.31+: mdp.3 stops (no more annexations)? (BDD #20)
- [ ] Full game: error.log clean of rebalance-related errors? (observation)

### Post-Game
- [ ] Run `rebalance_verify.py error.log` — any issues?
- [ ] Fill in `bdd.md` Y/N column
- [ ] Fill in `observe.md` notes
- [ ] Run `python run_test.py` → check report.html for assertions

---

## File Locations

| Script | Purpose | Run From |
|--------|---------|----------|
| `pretest_checklist.py` | Pre-launch validation | `testbook/v1/testkit/checks/` |
| `rebalance_verify.py` | Post-game log/conflict check | `testbook/v1/testkit/checks/` |
| `run_test.py` | Master test harness | `testbook/v1/testkit/` |
| `bdd.md` | In-game observations | `testbook/v1/MyDiploPlayMod/` |
| `observe.md` | Notes by year | `testbook/MyDiploPlayMod/` |

---

## Notes

- **Run as PAN** for best visibility (start at war with SIN, can see blob-chain afterward)
- **Play until 1851** to verify subject annexation window
- **Monitor error.log** during play (can check in-game via console if needed)
- **Spot-check** resources (don't need to verify all 5 rubber/oil; 1-2 per nation is enough)
- **Soft-remove tags** (BIC/PRU/EGY/SAR/SWE) should NOT start wars after day-1; others should continue until 1846

---

**Generated:** 2026-06-15  
**Test mods:** MyDiploPlayMod + Top40EcoBoostMod + ExpFightMod
