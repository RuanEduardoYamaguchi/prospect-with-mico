@echo off
rem PROSPECT WITH MICO: desliga tudo que o iniciar.bat ligou.
rem Backend (porta 5000), interface (porta 5173) e WhatsApp (Docker).
rem Seus leads e configuracoes ficam guardados.
cd /d "%~dp0"

echo Desligando o backend e a interface...
powershell -NoProfile -Command "foreach ($p in 5000,5173) { Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } }"

echo Desligando o WhatsApp (Docker)...
pushd "%~dp0whatsapp"
docker compose stop >nul 2>&1
popd

echo Pronto. Pra abrir de novo, use o iniciar.bat.
ping -n 4 127.0.0.1 >nul
