# Contrato backend/frontend (WhatsApp, campanhas, score, onboarding)

Base: fork do ProspectOS (github.com/nando0x/ProspectOS, MIT). Em cima dele
entram o envio pelo WhatsApp (Evolution API, via Docker, porta 8080), as
campanhas, a análise de oportunidade e o checklist de primeiros passos.

Este arquivo é o contrato entre backend e frontend. Mudou aqui, muda nos dois.

## Etapas do funil

As do ProspectOS, sem mudança: `novo, contatado, respondeu, fechou, recusou,
ignorado` (`backend/constantes.py`). O WhatsApp só automatiza as transições:

- envio com sucesso (individual ou campanha) → `contatado` + `proximo_followup` +3 dias
  (só se o lead estava `novo`; nunca rebaixa status)
- webhook recebe mensagem do lead → `respondeu`
- resposta de opt-out ("não tenho interesse", "sair", "pare", "remover") →
  `recusou` + `wa_optout = 1` (nunca mais entra em campanha)

Toda transição grava em `historico_status`, como `rotas_leads.atualizar_status`.
Toda mensagem (enviada ou recebida) vai pra `mensagens_conversa` (canal `maps`,
`lead_ref = place_id`, origem `app` pra enviada, `whatsapp` pra recebida),
então aparece sozinha no cockpit de conversa que já existe.

## Faixas de nota (score)

| Score | Abordagem |
|---|---|
| 70+ | manual: abordagem personalizada (amostra, áudio, PDF). Campanha não pega por padrão |
| 40 a 69 | campanha automática (filtro padrão `score_min=40, score_max=69`) |
| < 40 | não abordar |

As faixas são o padrão (filtro da campanha); mude à vontade.

## Resposta automática por IA (`backend/whatsapp/autoresponder.py`)

Mensagem do lead (canal `maps`) aciona a IA (`ia.analisar_conversa_com_fallback`,
o mesmo analista do cockpit manual) pra responder sozinha, até a leitura dela
chegar em `negociacao` ou `fechamento` - aí ela liga `leads.wa_ia_pausada`
(permanente) e manda um aviso pro responsável pela própria Evolution
(`NUMERO_NOTIFICACAO_QUALIFICACAO` no `backend/.env`; sem a variável, ninguém é avisado), sem
responder mais nada pro lead. A mesma coluna liga se o vendedor responder
manualmente pelo celular (webhook detecta via `fromMe` fora do app), pra IA
nunca responder por cima dele. Resposta automática não passa pelo teto do
aquecimento (é conversa, não prospecção fria) e usa a mesma porta de saída
do envio manual (`campanha.registrar_envio_manual`), então entra em
`wa_envios` e no cockpit normalmente.

Interruptor geral: config `wa_autoresposta_ativa` (`"1"`/`"0"`, padrão ligada).
Desligada, o autoresponder sai cedo: não responde e também não avisa quando um
lead qualifica. O que chegou nesse período não é respondido depois. Leads que
foram respondidos pelo celular ficam pausados (`wa_ia_pausada`) e precisam ser
retomados um por um na Conversa. A checagem roda no começo e de novo logo
antes de enviar, então desligar durante a análise da IA também impede o envio.

- `GET /api/whatsapp/autoresposta` -> `{"ativa": bool}`
- `POST /api/whatsapp/autoresposta` body `{"ativa": bool}` -> `{"ativa": bool}`
  (400 se não for booleano)
- `POST /api/leads/<place_id>/ia-pausada` body `{"pausada": bool}` ->
  `{"ok": true, "pausada": bool}` (404 lead inexistente, 400 se não for
  booleano). Liga/desliga `leads.wa_ia_pausada` por lead, também pra religar
  um lead que a IA pausou ao qualificar.

## Tabelas novas (dono: `backend/whatsapp/schema.py`)

- `leads.wa_optout INTEGER NOT NULL DEFAULT 0`
- `leads.wa_ia_pausada INTEGER NOT NULL DEFAULT 0` (resposta automática
  desligada pra sempre - lead qualificou ou vendedor assumiu manualmente)
- `wa_envios(id, place_id, telefone, texto, status, erro, campanha_id, id_externo, enviado_em)`
  status: `enviado | falhou | pulado`
- `wa_campanhas(id, nome, template, config_json, status, total, enviados, falhas, pulados, criada_em, atualizada_em, finalizada_em, ultimo_erro)`
  status: `rodando | pausada | concluida | parada | interrompida`
- `wa_fila(id, campanha_id, place_id, telefone, ordem, estado, texto)`
  estado: `pendente | enviado | falhou | pulado`

- `analises_oportunidade(id, place_id, recomendacao, oportunidade, evidencias, impacto, solucao, micro_demo, confianca, motivo_nao_abordar, desconhecido, angulo, score_no_momento, provedor, criada_em)`
  (dono: `backend/microdemo/schema.py`). `evidencias` e `desconhecido` são JSON (lista de strings).
  recomendacao: `abordar_com_demo | abordar_sem_demo | nao_abordar`; micro_demo: chave do
  catálogo (`agendamento | pedido`) ou `nenhuma`; confianca: `alta | media | baixa`

Colunas novas de `backend/importar_kaptar.py`: `leads.origem TEXT` (`maps` | `kaptar`).

## Endpoints

Todos JSON, erro sempre `{"erro": "mensagem em português"}` com status 4xx/5xx.

### WhatsApp (`backend/rotas_whatsapp.py`)

- `GET /api/whatsapp/estado` →
  `{evolution_ok: bool, conectado: bool, estado: "open"|"connecting"|"close"|"indisponivel", numero: string|null, instancia: string}`
- `POST /api/whatsapp/conectar` → `{estado, qr_base64: string|null}` (data URL `data:image/png;base64,...` ou null se já conectado)
- `POST /api/whatsapp/desconectar` → `{ok: true}`
- `GET /api/whatsapp/aquecimento` →
  `{dia_do_chip: int, teto_hoje: int, enviados_hoje: int, restantes_hoje: int, falhas_ontem: int}`
  Teto: 15 no dia 1, +5 por dia sem falha grave, até 150. Dia com 5+ falhas não sobe.
  O início conta do primeiro envio registrado (config `wa_aquecimento_inicio`).
- `POST /api/whatsapp/enviar` body `{place_id, texto, followup?: bool}` →
  `{ok: true, envio: Envio}`. Recusa (400) se: lead com optout, texto vazio,
  teto do dia esgotado, WhatsApp desconectado, número que já recebeu (a não ser
  com `followup: true`). Com `followup: true` e lead em `respondeu`/`fechou`, o
  teto do dia não trava (é conversa, não prospecção fria). Link é permitido aqui.
- `POST /api/whatsapp/enviar-numero` body `{telefone, texto}` → `{ok: true, numero}`.
  Envio avulso pra um número que não precisa estar cadastrado como lead (teste,
  contato pessoal). Não passa pelas travas de campanha (optout, já recebeu
  antes, teto do aquecimento) - só exige WhatsApp conectado e texto não vazio.
  Se o número bater com um lead do Maps já cadastrado, grava no cockpit dele
  normalmente.
- `POST /api/whatsapp/webhook` → recebe eventos da Evolution (`messages.upsert`,
  `connection.update`). Sempre 200 (processa numa thread separada pra não
  travar o ACK). Não é chamado pelo frontend. Mensagem de lead do canal `maps`
  aciona a resposta automática por IA, ver seção abaixo.

### Campanhas (`backend/rotas_whatsapp.py`)

`Filtros`:
```json
{ "nicho": "string|null", "cidade": "string|null", "status": ["novo"],
  "score_min": 40, "score_max": 69, "sem_site": false, "sem_instagram": false,
  "max_avaliacoes": null, "so_celular": true, "pular_contatados": true }
```
`Ritmo` (padrões):
```json
{ "intervalo_min_s": 45, "intervalo_max_s": 120, "pausa_a_cada": 10, "pausa_s": 600,
  "janela_inicio": "09:00", "janela_fim": "18:00" }
```

- `POST /api/campanhas/previa` body `{filtros, template, limite}` →
  `{leads: [{place_id, nome, telefone, nicho, cidade, score, site_status, texto_exemplo}], total: int, descartados: {motivo: int}, teto_restante: int, aviso: string|null}`
  `aviso` preenchido quando `total > teto_restante`.
- `POST /api/campanhas` body `{nome?, filtros, template, limite, ritmo, checar_whatsapp: true}` →
  `{campanha: Campanha}`. 400 se: template com link (`http`, `www.`, `.com`, `.br`, `wa.me`),
  já existe campanha rodando/pausada/interrompida, WhatsApp desconectado, lista vazia.
- `GET /api/campanhas` → `{ativa: Campanha|null, historico: Campanha[]}` (últimas 50)
- `POST /api/campanhas/<id>/parar` → `{campanha}` (status `pausada`)
- `POST /api/campanhas/<id>/retomar` → `{campanha}` (continua do próximo pendente)
- `POST /api/campanhas/<id>/descartar` → `{campanha}` (status `parada`, pendentes viram `pulado`)

`Campanha`:
```json
{ "id": 1, "nome": "...", "status": "rodando", "template": "...",
  "total": 30, "enviados": 4, "falhas": 0, "pulados": 1,
  "proximo_envio_em": "2026-09-21T15:02:10" , "aguardando_janela": false,
  "ultimo_erro": null, "criada_em": "...", "finalizada_em": null,
  "ultimos": [{"nome": "...", "telefone": "...", "status": "enviado", "enviado_em": "..."}] }
```

Regras da campanha:
intervalo aleatório, pausa longa a cada N, fora da janela espera (não para),
5 falhas seguidas → `pausada` com `ultimo_erro`, respeita o teto do aquecimento
(atingiu → espera o dia seguinte dentro da janela), checa número na Evolution
antes (sem WhatsApp → `pulado`). Estado 100% no banco: se o backend reiniciar,
campanha `rodando` vira `interrompida` e a UI oferece retomar/descartar.

Template: `{{nome}}`, `{{primeiro_nome}}`, `{{nicho}}`, `{{cidade}}`, `{{nota}}`,
`{{avaliacoes}}` e variação `{Oi|Olá|Bom dia}`.

### Análise de oportunidade (`backend/rotas_microdemo.py`)

`Analise` = `{id, recomendacao, oportunidade, evidencias: string[], impacto, solucao,
micro_demo, confianca, motivo_nao_abordar, desconhecido: string[], angulo,
score_no_momento: int, provedor: string, criada_em: string, avisos?: string[]}`
(`avisos` só vem na resposta do POST).

- `GET /api/leads/<place_id>/oportunidade` → `{analise: Analise|null, score: int, score_min: int}`;
  404 se o lead não existe
- `POST /api/leads/<place_id>/oportunidade/analisar` → `{analise: Analise}`. 404 lead
  inexistente; 400 quando o score está abaixo do mínimo
  (`"o score deste lead (58) está abaixo do mínimo para análise (70)"`); 500 sem IA disponível
- `GET /api/configuracoes/analise-oportunidade` → `{score_min: int}` (padrão 70)
- `POST /api/configuracoes/analise-oportunidade` body `{score_min: int}` (0 a 100) →
  `{score_min: int}`; 400 se não for inteiro nessa faixa

### Importação (`backend/rotas_importar.py`)

- `POST /api/importar/kaptar` body `{conteudo: string, nicho_padrao?: string, cidade_padrao?: string}` →
  `{importados: int, atualizados: int, descartados: {motivo: int}}`

### Onboarding (`backend/rotas_onboarding.py`)

- `GET /api/onboarding` →
  `{ia_configurada: bool, places_configurada: bool, perfil_preenchido: bool,
  estrategia_personalizada: bool, total_leads: int, leads_contatados: int}`.
  Só lê estado local (cofre de credenciais, banco, arquivos) e nunca devolve o
  valor de uma chave. `estrategia_personalizada` é falso enquanto o texto ainda
  tem trechos `[PREENCHER: ...]` do modelo.

### Estratégia de abordagem (`backend/rotas_config.py`)

- `GET /api/configuracoes/estrategia-abordagem` → `{texto, maximo, modelo}`.
  `texto` é a estratégia da instalação (`backend/estrategia_abordagem.md`, fora
  do Git); `modelo` é `estrategia_abordagem.exemplo.md`, o ponto de partida.
- `POST /api/configuracoes/estrategia-abordagem` body `{texto}` → `{ok: true}`.

Na campanha, template com `[PREENCHER` ainda no texto é recusado (400), igual a
template com link.
