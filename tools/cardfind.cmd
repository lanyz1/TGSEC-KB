@echo off
chcp 65001 >nul
setlocal
set "KB=C:\Users\Administrator\.dsh\tgsec-kb"
set "PY=C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
set "ARSENAL_SKILLS=%KB%\hermes-skills"
set "ARSENAL_DB=%KB%\arsenal\arsenal.db"
set "ARSENAL_DIR=%KB%\tools\arsenal"
set "PYTHONIOENCODING=utf-8"
"%PY%" "%KB%\tools\arsenal\skill_find.py" %*
