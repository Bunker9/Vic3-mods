@echo off
REM Double-click to re-run the test framework (regenerates the HTML report from the current
REM mod files + bdd.md answers + game logs). Then press F5 in your browser to see the update.
REM Pass a mod name to limit to one mod, e.g.:  validate.bat Top40EcoBoostMod
cd /d "%~dp0"
python testkit\run_test.py %*
echo.
echo ============================================================
echo Done. Now press F5 in your browser to refresh the report.
echo ============================================================
pause
