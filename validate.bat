@echo off
REM Legacy double-click entry. The v1 harness moved to v1\ on 2026-06-18; this thin
REM forwarder preserves the old root entry point. Passes through any mod-name argument.
REM (For the active v2 report run:  python v2\run_v2.py )
cd /d "%~dp0"
call v1\validate.bat %*
