# Prepara o primeiro uso do PROSPECT WITH MICO.
#
# - Cria o backend\.env a partir do modelo (vazio: as chaves de IA e do Google
#   você cola pela tela Configurações do sistema, ou aqui no arquivo).
# - Cria o whatsapp\.env com a chave da API e a senha do banco GERADAS AQUI, na
#   sua máquina, de forma aleatória. Nada disso sai do seu computador.
#
# Seguro de rodar de novo: nunca sobrescreve um .env que já existe.
# Uso: dois cliques em configurar.bat (o iniciar.bat também chama sozinho).

$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Nova-Chave([int]$bytes) {
    $buffer = New-Object byte[] $bytes
    $gerador = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $gerador.GetBytes($buffer)
    $gerador.Dispose()
    return ([System.BitConverter]::ToString($buffer) -replace "-", "").ToLower()
}

Write-Host ""
Write-Host "PROSPECT WITH MICO - preparando o primeiro uso" -ForegroundColor Cyan
Write-Host ""

# 1. backend\.env
$envBackend = Join-Path $raiz "backend\.env"
if (Test-Path $envBackend) {
    Write-Host "[ok] backend\.env ja existe, mantido." -ForegroundColor DarkGray
} else {
    Copy-Item (Join-Path $raiz "backend\.env.example") $envBackend
    Write-Host "[ok] Criado backend\.env (sem chaves: voce cola as suas)." -ForegroundColor Green
}

# 2. whatsapp\.env
$envWhatsapp = Join-Path $raiz "whatsapp\.env"
if (Test-Path $envWhatsapp) {
    Write-Host "[ok] whatsapp\.env ja existe, mantido." -ForegroundColor DarkGray
} else {
    $modelo = [System.IO.File]::ReadAllText((Join-Path $raiz "whatsapp\.env.example"), $utf8)
    $conteudo = $modelo.Replace("__GERAR_CHAVE_DA_API__", (Nova-Chave 32)).Replace("__GERAR_SENHA_DO_BANCO__", (Nova-Chave 24))
    [System.IO.File]::WriteAllText($envWhatsapp, $conteudo, $utf8)
    Write-Host "[ok] Criado whatsapp\.env com chave da API e senha do banco aleatorias." -ForegroundColor Green
}

Write-Host ""
Write-Host "Pronto. Proximo passo: dois cliques em iniciar.bat." -ForegroundColor Cyan
Write-Host "O sistema abre no navegador e mostra os Primeiros passos (chaves de IA e do Google)."
Write-Host ""
