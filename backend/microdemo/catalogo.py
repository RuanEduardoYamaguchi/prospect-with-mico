"""Modelos de micro-demo disponíveis. A análise de oportunidade escolhe uma
destas chaves (ou "nenhuma"); o prompt é montado a partir daqui, então modelo
novo é só uma entrada a mais."""

CATALOGO = {
    "agendamento": {
        "descricao": "fluxo de agendamento: escolher o serviço, escolher um horário e confirmar",
        "quando_usar": (
            "negócio que atende com hora marcada (clínica, estética, pet shop de banho e tosa) "
            "e onde quem descobre pelo Google não encontra um jeito simples de marcar"
        ),
    },
    "pedido": {
        "descricao": "fluxo de pedido: ver os itens, montar o pedido e finalizar",
        "quando_usar": (
            "negócio que vende itens (café, confeitaria, delivery) e onde quem descobre pelo "
            "Google não encontra cardápio nem um jeito simples de pedir"
        ),
    },
}
