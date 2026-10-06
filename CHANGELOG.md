# Changelog

O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [1.0.0] - Edição pública

Primeira versão pública do PROSPECT WITH MICO (MICO TECH), derivada do
[ProspectOS](https://github.com/nando0x/ProspectOS) (MIT).

### Adicionado

- **Primeiros passos**: checklist no Painel e na página "Como usar" que lê o estado real da
  instalação (chaves, perfil, estratégia, primeira busca, WhatsApp) e marca sozinho.
- `configurar.bat`: cria os arquivos `.env` e gera, na máquina de quem instala, a chave da API
  e a senha do banco do WhatsApp.
- `iniciar.bat` verifica Python e Node, configura o primeiro uso e sobe tudo.
- Modelo de estratégia de abordagem (`backend/estrategia_abordagem.exemplo.md`) com botão
  "Começar pelo modelo" e bloqueio de salvar enquanto houver `[PREENCHER: ...]`.
- Templates de campanha genéricos, e a campanha recusa texto que ainda tenha `[PREENCHER: ...]`.
- Envio pelo WhatsApp (Evolution API), campanhas com ritmo humano, aquecimento do chip,
  opt-out, resposta automática por IA, análise de oportunidade e importação de CSV.
- Busca de negócios pela Google Places API oficial, com teto mensal de consultas.
- Documentação: README, `docs/PRIMEIROS-PASSOS.md`, `whatsapp/README.md`.

### Alterado

- Nenhuma chave de API, número de telefone ou dado de cliente acompanha o projeto. Todas as chaves
  são do usuário (`backend/.env.example` vem em branco).
- `NUMERO_OFICIAL` e `NUMERO_NOTIFICACAO_QUALIFICACAO` deixam de ter valor padrão: sem a variável,
  a trava de número oficial fica desligada e nenhum aviso de lead quente é enviado.
- A comparação do número oficial ignora o 55 e o nono dígito.
- A estratégia de abordagem da instalação (`backend/estrategia_abordagem.md`) fica fora do Git.
- Pesos do score sem nicho-alvo por padrão (`nichos_alvo` vazio).
- Docker: Evolution só escuta em `127.0.0.1`, Postgres e Redis sem porta publicada, senha do banco
  obrigatória e aleatória.

### Removido

- Instalador e app desktop do projeto original.
- Importação do histórico do painel antigo do WhatsApp.
- Documentação e script do fluxo antigo por linha de comando.
