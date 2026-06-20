@echo off
REM One-click v2 testbook report (the ACTIVE engine). Double-click, or pass a mod name to limit
REM to one mod (e.g. run.bat Top40EcoBoostMod), or --open to open the report in the browser.
python "%~dp0run_v2.py" %*
echo.
echo ============================================================
echo Done. Refresh MAIN-^<branch^>-testing.html (F5), or re-run with --open.
echo ============================================================
pause
