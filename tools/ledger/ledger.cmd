@echo off
chcp 65001 >nul
setlocal
set "KB=C:\Users\Administrator\.dsh\tgsec-kb"
set "PY=C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
"%PY%" "%KB%\tools\ledger\ledger.py" %*
