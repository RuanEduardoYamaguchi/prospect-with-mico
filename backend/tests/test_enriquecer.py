"""Testes do enriquecimento defensivo de perfis do Instagram - o instagrapi é
substituído por um cliente fake: nenhuma chamada de rede real, nenhuma sessão."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "instagram"))

import enriquecer_perfis
from instagrapi.exceptions import ChallengeRequired, LoginRequired, PleaseWaitFewMinutes


def perfil_fake(username):
    return SimpleNamespace(
        is_private=False,
        full_name=f"Nome {username}",
        biography=f"Bio {username}",
        follower_count=100,
        is_business=True,
        external_url=None,
    )


class ClienteFake:
    """Devolve perfis fake ou levanta a exceção programada para o username."""

    def __init__(self, erros_por_username=None):
        self.erros_por_username = erros_por_username or {}
        self.consultados = []

    def user_info_by_username(self, username):
        self.consultados.append(username)
        erro = self.erros_por_username.get(username)
        if erro:
            raise erro
        return perfil_fake(username)


@pytest.fixture
def sem_espera(monkeypatch):
    monkeypatch.setattr(enriquecer_perfis, "_dormir_com_jitter", lambda delay: None)


def criar_json_comentarios(tmp_path, usernames):
    dados = {
        "post_url": "https://www.instagram.com/p/ABC/",
        "total_comentarios": len(usernames),
        "comentarios": [{"username": u, "texto": f"comentário de {u}"} for u in usernames],
    }
    caminho = tmp_path / "post_123.json"
    caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return caminho


def usar_cliente(monkeypatch, cliente):
    monkeypatch.setattr(enriquecer_perfis, "carregar_sessao", lambda: cliente)


class TestEnriquecimento:
    def test_fluxo_completo(self, tmp_path, monkeypatch, sem_espera):
        cliente = ClienteFake()
        usar_cliente(monkeypatch, cliente)
        caminho = criar_json_comentarios(tmp_path, ["user1", "user2"])

        saida = enriquecer_perfis.enriquecer_perfis(caminho)

        dados = json.loads(saida.read_text(encoding="utf-8"))
        assert [p["username"] for p in dados["perfis"]] == ["user1", "user2"]
        assert dados["perfis"][0]["full_name"] == "Nome user1"
        assert cliente.consultados == ["user1", "user2"]

    def test_salva_parcial_a_cada_perfil(self, tmp_path, monkeypatch, sem_espera):
        caminho = criar_json_comentarios(tmp_path, ["user1", "user2"])
        saida_esperada = caminho.with_name(caminho.stem + "_enriquecido.json")

        class ClienteQueObservaParcial(ClienteFake):
            def user_info_by_username(self, username):
                if username == "user2":
                    # antes de consultar o 2º, o 1º já precisa estar salvo em disco
                    parcial = json.loads(saida_esperada.read_text(encoding="utf-8"))
                    assert [p["username"] for p in parcial["perfis"]] == ["user1"]
                return super().user_info_by_username(username)

        usar_cliente(monkeypatch, ClienteQueObservaParcial())
        enriquecer_perfis.enriquecer_perfis(caminho)

    def test_retomada_pula_perfis_ja_consultados(self, tmp_path, monkeypatch, sem_espera):
        cliente = ClienteFake()
        usar_cliente(monkeypatch, cliente)
        caminho = criar_json_comentarios(tmp_path, ["user1", "user2", "user3"])

        # simula rodada anterior: user1 ok, user2 tinha dado erro (deve ser retentado)
        parcial = {
            "post_url": "https://www.instagram.com/p/ABC/",
            "perfis": [
                {"username": "user1", "comentarios": ["x"], "full_name": "Nome user1"},
                {"username": "user2", "comentarios": ["y"], "erro": "rate limit da rodada anterior"},
            ],
        }
        saida = caminho.with_name(caminho.stem + "_enriquecido.json")
        saida.write_text(json.dumps(parcial, ensure_ascii=False), encoding="utf-8")

        enriquecer_perfis.enriquecer_perfis(caminho)

        assert cliente.consultados == ["user2", "user3"]  # user1 não é consultado de novo
        dados = json.loads(saida.read_text(encoding="utf-8"))
        assert {p["username"] for p in dados["perfis"]} == {"user1", "user2", "user3"}
        assert not any(p.get("erro") for p in dados["perfis"])


class TestInterrupcoes:
    def test_checkpoint_para_na_hora_e_salva_parcial(self, tmp_path, monkeypatch, sem_espera):
        cliente = ClienteFake(erros_por_username={"user2": ChallengeRequired()})
        usar_cliente(monkeypatch, cliente)
        caminho = criar_json_comentarios(tmp_path, ["user1", "user2", "user3"])

        with pytest.raises(enriquecer_perfis.AnaliseInterrompida, match="checkpoint"):
            enriquecer_perfis.enriquecer_perfis(caminho)

        # parou no user2: user3 nunca foi consultado (não queima a conta à toa)
        assert cliente.consultados == ["user1", "user2"]
        parcial = json.loads(
            caminho.with_name(caminho.stem + "_enriquecido.json").read_text(encoding="utf-8")
        )
        assert [p["username"] for p in parcial["perfis"]] == ["user1"]

    def test_sessao_expirada_para_na_hora(self, tmp_path, monkeypatch, sem_espera):
        cliente = ClienteFake(erros_por_username={"user1": LoginRequired()})
        usar_cliente(monkeypatch, cliente)
        caminho = criar_json_comentarios(tmp_path, ["user1", "user2"])

        with pytest.raises(enriquecer_perfis.AnaliseInterrompida, match="sessão do Instagram expirou"):
            enriquecer_perfis.enriquecer_perfis(caminho)
        assert cliente.consultados == ["user1"]

    def test_rate_limit_persistente_desiste_apos_3_seguidos(self, tmp_path, monkeypatch, sem_espera):
        usernames = ["u1", "u2", "u3", "u4", "u5"]
        cliente = ClienteFake(
            erros_por_username={u: PleaseWaitFewMinutes() for u in usernames}
        )
        usar_cliente(monkeypatch, cliente)
        caminho = criar_json_comentarios(tmp_path, usernames)

        with pytest.raises(enriquecer_perfis.AnaliseInterrompida, match="rate limit"):
            enriquecer_perfis.enriquecer_perfis(caminho)

        # desistiu no 3º rate limit consecutivo - u4/u5 nunca foram tentados
        assert cliente.consultados == ["u1", "u2", "u3"]

    def test_rate_limit_isolado_nao_interrompe(self, tmp_path, monkeypatch, sem_espera):
        cliente = ClienteFake(erros_por_username={"user1": PleaseWaitFewMinutes()})
        usar_cliente(monkeypatch, cliente)
        caminho = criar_json_comentarios(tmp_path, ["user1", "user2"])

        saida = enriquecer_perfis.enriquecer_perfis(caminho)

        dados = json.loads(saida.read_text(encoding="utf-8"))
        assert cliente.consultados == ["user1", "user2"]
        assert "erro" in dados["perfis"][0]
        assert "erro" not in dados["perfis"][1]

    def test_backoff_cresce_com_rate_limit(self, tmp_path, monkeypatch):
        esperas = []
        monkeypatch.setattr(enriquecer_perfis, "_dormir_com_jitter", esperas.append)
        cliente = ClienteFake(
            erros_por_username={"u1": PleaseWaitFewMinutes(), "u2": PleaseWaitFewMinutes()}
        )
        usar_cliente(monkeypatch, cliente)
        caminho = criar_json_comentarios(tmp_path, ["u1", "u2", "u3"])

        enriquecer_perfis.enriquecer_perfis(caminho)

        # 8s → dobra pra 16 após 1º rate limit → dobra pra 32 após o 2º
        assert esperas == [16, 32]
