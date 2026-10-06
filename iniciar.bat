@echo off
rem PROSPECT WITH MICO: sobe a ferramenta inteira com dois cliques.
rem Backend (Flask) + interface (Vite) + Evolution API (WhatsApp, via Docker).
rem Na primeira vez instala o que faltar. O Docker so e preciso pro WhatsApp.
cd /d "%~dp0"

set PASTA_BACKEND=%~dp0backend
set PASTA_FRONTEND=%~dp0frontend
set PASTA_WHATSAPP=%~dp0whatsapp
set PASTA_LOGS=%~dp0logs
set PYTHON=%PASTA_BACKEND%\.venv\Scripts\python.exe

where py >nul 2>&1
if errorlevel 1 (
    echo Python nao encontrado. Instale o Python 3.11 ou mais novo em https://www.python.org/downloads/
    echo Na instalacao, marque "Add python.exe to PATH" e rode este arquivo de novo.
    pause
    exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
    echo Node.js nao encontrado. Instale o Node 20 ou mais novo em https://nodejs.org/ e rode este arquivo de novo.
    pause
    exit /b 1
)

rem primeira vez: cria os .env (a chave do WhatsApp e a senha do banco sao geradas aqui)
set PRECISA_CONFIGURAR=0
if not exist "%PASTA_BACKEND%\.env" set PRECISA_CONFIGURAR=1
if not exist "%PASTA_WHATSAPP%\.env" set PRECISA_CONFIGURAR=1
if "%PRECISA_CONFIGURAR%"=="1" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0configurar.ps1"

if not exist "%PASTA_LOGS%" mkdir "%PASTA_LOGS%"
if not exist "%PASTA_LOGS%\vazio.txt" type nul > "%PASTA_LOGS%\vazio.txt"

if not exist "%PYTHON%" (
    echo Criando o ambiente do Python, so na primeira vez...
    py -m venv "%PASTA_BACKEND%\.venv"
    "%PYTHON%" -m pip install -q -r "%PASTA_BACKEND%\requirements.txt"
)
if not exist "%PASTA_FRONTEND%\node_modules" (
    echo Instalando a interface, so na primeira vez...
    call npm --prefix "%PASTA_FRONTEND%" install --no-fund --no-audit
)

echo Subindo a Evolution API (WhatsApp)...
pushd "%PASTA_WHATSAPP%"
docker compose up -d
if errorlevel 1 (
    echo.
    echo Docker nao respondeu. Abra o Docker Desktop, espere "Engine running" e rode de novo.
    echo O PROSPECT WITH MICO abre mesmo assim, mas sem envio pelo WhatsApp.
    echo.
)
popd

echo Verificando se o backend ja esta rodando...
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri http://127.0.0.1:5000/api/metricas -UseBasicParsing -TimeoutSec 1 | Out-Null; exit 0 } catch { exit 1 }"

if %errorlevel%==0 (
    echo Backend ja estava rodando.
) else (
    echo Iniciando o backend...
    powershell -NoProfile -Command "Start-Process '%PYTHON%' -ArgumentList 'app.py' -WorkingDirectory '%PASTA_BACKEND%' -WindowStyle Hidden -RedirectStandardOutput '%PASTA_LOGS%\backend-saida.log' -RedirectStandardError '%PASTA_LOGS%\backend-erro.log' -RedirectStandardInput '%PASTA_LOGS%\vazio.txt'"
)

echo Verificando se a interface ja esta rodando...
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri http://localhost:5173 -UseBasicParsing -TimeoutSec 1 | Out-Null; exit 0 } catch { exit 1 }"

if %errorlevel%==0 (
    echo Interface ja estava rodando.
) else (
    echo Iniciando a interface...
    powershell -NoProfile -Command "Start-Process cmd -ArgumentList '/c','npm run dev' -WorkingDirectory '%PASTA_FRONTEND%' -WindowStyle Hidden -RedirectStandardOutput '%PASTA_LOGS%\frontend-saida.log' -RedirectStandardError '%PASTA_LOGS%\frontend-erro.log' -RedirectStandardInput '%PASTA_LOGS%\vazio.txt'"
    timeout /t 4 /nobreak >nul
)

start http://localhost:5173
