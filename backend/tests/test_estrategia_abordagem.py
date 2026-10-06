"""Estratégia de abordagem (.md) que manda no gerador de mensagens."""

import ia


def test_sem_estrategia_mantem_o_padrao_de_site():
    prompt = ia.montar_prompt_contato("Clínica Sorriso", "Dentista", "Rua X", 4.9)
    assert "site profissional" in prompt
    assert "ESTRATÉGIA DE ABORDAGEM" not in ia.montar_system_copywriter("WhatsApp")


def test_estrategia_entra_no_system_e_troca_a_oferta():
    ia.CAMINHO_ESTRATEGIA.write_text("Oferecer agenda no WhatsApp com lembrete.", encoding="utf-8")

    system = ia.montar_system_copywriter("WhatsApp")
    assert "ESTRATÉGIA DE ABORDAGEM" in system
    assert "agenda no WhatsApp com lembrete" in system

    prompt = ia.montar_prompt_contato("Clínica Sorriso", "Dentista", "Rua X", 4.9)
    assert "site profissional" not in prompt
    assert "ESTRATÉGIA DE ABORDAGEM" in prompt


def test_estrategia_manda_no_fechamento():
    ia.CAMINHO_ESTRATEGIA.write_text("Fechar sempre perguntando quem é o responsável.", encoding="utf-8")
    assert "ESTRATÉGIA DE ABORDAGEM" in ia.sortear_fechamento()


def test_arquivo_so_com_espacos_conta_como_sem_estrategia():
    ia.CAMINHO_ESTRATEGIA.write_text("   \n\n", encoding="utf-8")
    assert ia.ler_estrategia_abordagem() == ""


# ---------------------------------------------------------------------------
# Rotas de leitura/gravação (editor na tela de prospecção)
# ---------------------------------------------------------------------------

import app as app_module


def test_rota_salva_e_le_a_estrategia():
    cliente = app_module.app.test_client()
    resposta = cliente.post("/api/configuracoes/estrategia-abordagem",
                            json={"texto": "Oferecer agenda.\r\nSem link."})
    assert resposta.status_code == 200
    assert ia.CAMINHO_ESTRATEGIA.read_text(encoding="utf-8") == "Oferecer agenda.\nSem link."

    lido = cliente.get("/api/configuracoes/estrategia-abordagem").get_json()
    assert lido["texto"] == "Oferecer agenda.\nSem link."


def test_salvar_guarda_a_versao_anterior():
    ia.CAMINHO_ESTRATEGIA.write_text("versão 1", encoding="utf-8")
    app_module.app.test_client().post("/api/configuracoes/estrategia-abordagem", json={"texto": "versão 2"})
    assert ia.CAMINHO_ESTRATEGIA.with_suffix(".anterior.md").read_text(encoding="utf-8") == "versão 1"


def test_estrategia_longa_demais_e_recusada():
    resposta = app_module.app.test_client().post(
        "/api/configuracoes/estrategia-abordagem", json={"texto": "x" * (ia.MAX_CARACTERES_ESTRATEGIA + 1)}
    )
    assert resposta.status_code == 400
    assert not ia.CAMINHO_ESTRATEGIA.exists()


def test_rota_devolve_o_modelo_mesmo_sem_estrategia_salva():
    dados = app_module.app.test_client().get("/api/configuracoes/estrategia-abordagem").get_json()
    assert dados["texto"] == ""
    assert "[PREENCHER" in dados["modelo"]
    assert len(dados["modelo"]) < ia.MAX_CARACTERES_ESTRATEGIA


def test_modelo_nao_traz_telefone_email_nem_link_de_ninguem():
    import re

    modelo = ia.ler_modelo_estrategia()
    assert not re.search(r"\d{8,}", modelo)
    assert "@" not in modelo
    assert "http" not in modelo.lower()


def test_estrategia_com_marcador_vale_como_vazia():
    ia.CAMINHO_ESTRATEGIA.write_text("Aqui é o [PREENCHER: seu nome].", encoding="utf-8")
    assert ia.ler_estrategia_abordagem() == ""
    assert "PREENCHER" not in ia.montar_system_copywriter("WhatsApp")


def test_rota_recusa_salvar_estrategia_com_marcador():
    resposta = app_module.app.test_client().post(
        "/api/configuracoes/estrategia-abordagem", json={"texto": "Sou o [PREENCHER: seu nome]."}
    )
    assert resposta.status_code == 400
    assert not ia.CAMINHO_ESTRATEGIA.exists()
