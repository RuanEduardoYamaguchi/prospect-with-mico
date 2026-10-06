@echo off
rem Prepara o primeiro uso: cria os arquivos .env (com chaves geradas na sua maquina).
rem Seguro de rodar de novo, nunca sobrescreve o que ja existe.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0configurar.ps1"
pause
