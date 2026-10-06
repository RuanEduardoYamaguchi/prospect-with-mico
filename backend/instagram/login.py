"""
Login único no Instagram, salvando a sessão para os outros scripts usarem.

Uso:
    py login.py <seu_usuario>

Vai pedir a senha de forma interativa (não aparece na tela ao digitar).
Se o Instagram pedir código de verificação (2FA), o script pergunta na hora.
"""

import getpass
import sys
from pathlib import Path

from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired

# permite achar o paths.py do backend também quando rodado standalone
sys.path.insert(0, str(Path(__file__).parent.parent))
from paths import DIR_DADOS  # noqa: E402

PASTA_SESSAO = DIR_DADOS / "instagram" / "sessao"


def main() -> None:
    if len(sys.argv) != 2:
        print("Uso: py login.py <seu_usuario>")
        sys.exit(1)

    usuario = sys.argv[1]
    senha = getpass.getpass(f"Senha do Instagram para {usuario}: ")

    cliente = Client()

    try:
        cliente.login(usuario, senha)
    except TwoFactorRequired:
        codigo = input("Código de verificação (2FA): ").strip()
        cliente.login(usuario, senha, verification_code=codigo)

    PASTA_SESSAO.mkdir(parents=True, exist_ok=True)
    caminho_sessao = PASTA_SESSAO / f"session-{usuario}.json"
    cliente.dump_settings(caminho_sessao)

    print(f"Login feito com sucesso. Sessão salva em: {caminho_sessao}")


if __name__ == "__main__":
    main()
