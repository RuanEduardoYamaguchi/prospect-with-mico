"""Checklist de primeiros passos (/api/onboarding): reflete o que já está
configurado, sem chamar nenhuma API externa."""

import sqlite3

import pytest

import app as app_module
import db
import ia
import processar


@pytest.fixture
def banco(tmp_path, monkeypatch):
    caminho = tmp_path / "leads_teste.db"
    monkeypatch.setattr(db, "CAMINHO_BANCO", caminho)
    conexao = sqlite3.connect(caminho)
    try:
        processar.preparar_banco(conexao)
    finally:
        conexao.close()

    guardado = {}
    monkeypatch.setattr(db, "_keyring_obter", lambda chave: guardado.get(chave))
    monkeypatch.setattr(db, "_keyring_salvar", lambda chave, valor: guardado.__setitem__(chave, valor) or True)
    # nenhuma chave do ambiente de quem roda os testes pode vazar pra dentro
    for variavel in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY", "NVIDIA_API_KEY", "PLACES_API_KEY"):
        monkeypatch.delenv(variavel, raising=False)
    return caminho


def _inserir_lead(status="novo", place_id="p1"):
    conexao = db.conectar()
    try:
        conexao.execute(
            "INSERT INTO leads (place_id, nome, site_status, status, visto_em, atualizado_em) "
            "VALUES (?, 'Empresa Teste', 'sem_site', ?, '2026-01-01', '2026-01-01')",
            (place_id, status),
        )
        conexao.commit()
    finally:
        conexao.close()


def _checklist():
    resposta = app_module.app.test_client().get("/api/onboarding")
    assert resposta.status_code == 200
    return resposta.get_json()


def test_instalacao_nova_tem_tudo_pendente(banco):
    assert _checklist() == {
        "ia_configurada": False,
        "places_configurada": False,
        "perfil_preenchido": False,
        "estrategia_personalizada": False,
        "total_leads": 0,
        "leads_contatados": 0,
    }


def test_qualquer_chave_de_ia_conta_como_ia_configurada(banco):
    db.salvar_config("groq", "chave-de-teste")
    assert _checklist()["ia_configurada"] is True


def test_chave_do_places_e_independente_das_de_ia(banco):
    db.salvar_config("places", "chave-de-teste")
    dados = _checklist()
    assert dados["places_configurada"] is True
    assert dados["ia_configurada"] is False


def test_perfil_so_conta_com_nome_preenchido(banco):
    db.salvar_config("vendedor_nome", "   ")
    assert _checklist()["perfil_preenchido"] is False
    db.salvar_config("vendedor_nome", "Ana")
    assert _checklist()["perfil_preenchido"] is True


def test_estrategia_com_marcador_do_modelo_nao_conta(banco):
    ia.CAMINHO_ESTRATEGIA.write_text(ia.ler_modelo_estrategia(), encoding="utf-8")
    assert _checklist()["estrategia_personalizada"] is False


def test_estrategia_escrita_pelo_usuario_conta(banco):
    ia.CAMINHO_ESTRATEGIA.write_text("Ofereço agenda no WhatsApp pra clínicas.", encoding="utf-8")
    assert _checklist()["estrategia_personalizada"] is True


def test_conta_leads_e_leads_contatados(banco):
    _inserir_lead("novo", "p1")
    _inserir_lead("contatado", "p2")
    _inserir_lead("respondeu", "p3")
    dados = _checklist()
    assert dados["total_leads"] == 3
    assert dados["leads_contatados"] == 2


def test_resposta_nunca_expoe_valor_de_chave(banco):
    db.salvar_config("anthropic", "SEGREDO-NAO-VAZAR")
    resposta = app_module.app.test_client().get("/api/onboarding")
    assert "SEGREDO-NAO-VAZAR" not in resposta.get_data(as_text=True)
