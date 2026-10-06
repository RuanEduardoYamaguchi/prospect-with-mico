"""Testes de whatsapp/texto.py: spintax, variáveis, heurística de primeiro
nome e detecção de link. Tudo função pura, sem banco nem rede.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from whatsapp import texto


def rand_fixo(valor):
    """Substitui random.random() por um valor fixo, pra sortear_variacao ficar
    determinístico nos testes."""
    return lambda: valor


class TestSortearVariacao:
    def test_sem_chaves_nao_muda(self):
        assert texto.sortear_variacao("Oi, tudo bem?") == "Oi, tudo bem?"

    def test_escolhe_primeira_opcao_com_rand_zero(self):
        assert texto.sortear_variacao("{Oi|Olá|Bom dia}", rand=rand_fixo(0.0)) == "Oi"

    def test_escolhe_ultima_opcao_com_rand_quase_um(self):
        assert texto.sortear_variacao("{Oi|Olá|Bom dia}", rand=rand_fixo(0.99)) == "Bom dia"

    def test_duas_variacoes_na_mesma_mensagem(self):
        resultado = texto.sortear_variacao("{Oi|Olá}, {tudo bem|como vai}?", rand=rand_fixo(0.0))
        assert resultado == "Oi, tudo bem?"

    def test_texto_vazio(self):
        assert texto.sortear_variacao("") == ""
        assert texto.sortear_variacao(None) == ""


class TestPreencherVariaveis:
    def test_troca_variavel_simples(self):
        resultado = texto.preencher_variaveis("Oi {{nome}}!", {"nome": "Clínica Sorriso"})
        assert resultado == "Oi Clínica Sorriso!"

    def test_campo_ausente_vira_vazio(self):
        assert texto.preencher_variaveis("Oi {{nome}}!", {}) == "Oi !"

    def test_campo_none_vira_vazio(self):
        assert texto.preencher_variaveis("Nota: {{nota}}", {"nota": None}) == "Nota: "

    def test_numero_vira_string(self):
        assert texto.preencher_variaveis("Nota {{nota}}", {"nota": 4.8}) == "Nota 4.8"

    def test_variavel_desconhecida_no_template_vira_vazia(self):
        assert texto.preencher_variaveis("{{campo_que_nao_existe}}", {"nome": "x"}) == ""


class TestPrimeiroNome:
    def test_usa_responsavel_quando_existe(self):
        lead = {"nome": "Clínica Sorriso", "responsavel": "Dra. Fulana de Tal"}
        assert texto.primeiro_nome(lead) == "Fulana"

    def test_responsavel_com_parenteses_e_ignorado(self):
        lead = {"responsavel": "Beatriz (recepção)"}
        assert texto.primeiro_nome(lead) == "Beatriz"

    def test_nome_com_titulo_usa_segunda_palavra(self):
        lead = {"nome": "Dra. Fulana Odontologia"}
        assert texto.primeiro_nome(lead) == "Fulana"

    def test_nome_de_negocio_generico_fica_vazio(self):
        lead = {"nome": "Clínica Sorriso Odontologia"}
        assert texto.primeiro_nome(lead) == ""

    def test_nome_vazio(self):
        assert texto.primeiro_nome({}) == ""

    def test_nome_minusculo_nao_vira_nome_proprio(self):
        assert texto.primeiro_nome({"nome": "estúdio de estética"}) == ""


class TestMontarMensagem:
    def test_variaveis_e_variacao_juntas(self):
        lead = {"nome": "Clínica Sorriso", "nicho": "odontologia", "cidade": "Londrina",
                 "nota": 4.5, "num_avaliacoes": 80}
        resultado = texto.montar_mensagem("{Oi|Olá} {{nome}}, vi que vocês são referência em {{nicho}} em {{cidade}}!",
                                            lead, rand=rand_fixo(0.0))
        assert resultado == "Oi Clínica Sorriso, vi que vocês são referência em odontologia em Londrina!"

    def test_resultado_e_aparado(self):
        lead = {"nome": "X"}
        assert texto.montar_mensagem("  Oi {{nome}}  ", lead) == "Oi X"


class TestContemLink:
    def test_http_e_bloqueado(self):
        assert texto.contem_link("Olha esse link http://exemplo.com")

    def test_wa_me_e_bloqueado(self):
        assert texto.contem_link("Fala comigo aqui: wa.me/554199999999")

    def test_www_e_bloqueado(self):
        assert texto.contem_link("acesse www.exemplo.com.br")

    def test_texto_normal_passa(self):
        assert not texto.contem_link("Oi {{nome}}, tudo bem? Vi seu perfil no Google.")

    def test_vazio_nao_e_link(self):
        assert not texto.contem_link("")


class TestContemMarcadorPreencher:
    def test_marcador_do_modelo_e_detectado(self):
        assert texto.contem_marcador_preencher("Aqui é o [PREENCHER: seu nome], da [PREENCHER: sua empresa].")

    def test_texto_ja_preenchido_passa(self):
        assert not texto.contem_marcador_preencher("Aqui é a Ana, da Ana Digital.")

    def test_vazio_e_none_passam(self):
        assert not texto.contem_marcador_preencher("")
        assert not texto.contem_marcador_preencher(None)
