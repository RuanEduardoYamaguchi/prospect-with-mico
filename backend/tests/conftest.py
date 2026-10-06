"""Fixtures globais dos testes."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import ia


@pytest.fixture(autouse=True)
def sem_estrategia_personalizada(tmp_path, monkeypatch):
    """O gerador lê backend/estrategia_abordagem.md, que cada instalação edita à
    vontade. Os testes não podem depender do que está escrito lá: por padrão
    apontam pra um arquivo inexistente (= comportamento padrão da ferramenta).
    Teste que quer uma estratégia escreve em ia.CAMINHO_ESTRATEGIA."""
    monkeypatch.setattr(ia, "CAMINHO_ESTRATEGIA", tmp_path / "estrategia_abordagem.md")
