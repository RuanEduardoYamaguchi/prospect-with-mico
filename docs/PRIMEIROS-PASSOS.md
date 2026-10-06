# Primeiros passos no PROSPECT WITH MICO

Este guia leva você do zero até a primeira mensagem pronta, em uns 10 minutos
(sem contar o tempo de criar as contas nos provedores). O sistema também mostra
um checklist **Primeiros passos** no Painel que vai marcando sozinho o que você já fez.

- [1. O que instalar](#1-o-que-instalar)
- [2. Abrir o sistema](#2-abrir-o-sistema)
- [3. Chave do Google Places (busca de negócios)](#3-chave-do-google-places-busca-de-negócios)
- [4. Chave de IA (escreve as mensagens)](#4-chave-de-ia-escreve-as-mensagens)
- [5. Seu perfil e sua estratégia](#5-seu-perfil-e-sua-estratégia)
- [6. Primeira busca](#6-primeira-busca)
- [7. Primeira mensagem](#7-primeira-mensagem)
- [8. WhatsApp integrado (opcional)](#8-whatsapp-integrado-opcional)
- [9. A rotina do dia a dia](#9-a-rotina-do-dia-a-dia)
- [Problemas comuns](#problemas-comuns)

---

## 1. O que instalar

| Programa | Pra quê | Onde baixar |
|---|---|---|
| **Python 3.11 ou mais novo** | Roda o backend | https://www.python.org/downloads/ (marque **Add python.exe to PATH**) |
| **Node.js 20 ou mais novo** | Roda a interface | https://nodejs.org/ |
| **Docker Desktop** | Só para o WhatsApp integrado. Pode deixar pra depois | https://www.docker.com/products/docker-desktop/ |

Sistema: Windows 10 ou 11.

## 2. Abrir o sistema

1. Baixe o projeto e extraia numa pasta sua (por exemplo `C:\prospect-with-mico`).
2. Dê dois cliques em **`iniciar.bat`**.

Na primeira vez ele:
- cria os arquivos de configuração (`backend\.env` e `whatsapp\.env`). A chave do WhatsApp e a senha do banco do WhatsApp
  são **geradas aleatoriamente na sua máquina**, ninguém mais as conhece;
- instala as dependências (leva alguns minutos, só dessa vez);
- abre o sistema no navegador em **http://localhost:5173**.

Se o Docker não estiver aberto, tudo funciona normalmente, menos o envio pelo WhatsApp.

Pra fechar, é só fechar a aba. Para abrir de novo, `iniciar.bat` outra vez.

## 3. Chave do Google Places (busca de negócios)

É ela que acha os negócios no Google Maps. **Sem ela não há busca.**

1. Entre em https://console.cloud.google.com/ e crie um projeto (qualquer nome).
2. Em **APIs e serviços > Biblioteca**, procure **Places API (New)** e clique em **Ativar**.
3. Em **APIs e serviços > Credenciais**, clique em **Criar credenciais > Chave de API**. Copie a chave.
4. Recomendado: clique na chave criada e, em **Restrições de API**, restrinja ela à **Places API (New)**.
5. O Google exige uma **conta de faturamento ativa** no projeto, mesmo com a cota gratuita. Crie um **alerta de orçamento**
   no próprio Google Cloud para não ter surpresa.
6. No sistema: **Configurações > Google Places**, cole a chave e clique em **Validar e salvar**.

O sistema conta as consultas do mês e para em um teto (900 por padrão) para você ficar na cota gratuita.
Confira os limites e preços atuais do Google, que mudam de tempos em tempos.

## 4. Chave de IA (escreve as mensagens)

Configure **pelo menos uma**. Com várias, o sistema tenta uma e passa pra próxima se a cota acabar.

| Provedor | Onde pegar | Custo |
|---|---|---|
| Google Gemini | https://aistudio.google.com/apikey | Tem plano gratuito |
| Groq | https://console.groq.com/keys | Tem plano gratuito |
| NVIDIA Build | https://build.nvidia.com | Tem plano gratuito |
| Claude (Anthropic) | https://console.anthropic.com/settings/keys | Pago por uso |

No sistema: **Configurações > Chaves de API**, cole a chave no provedor e clique em **Salvar**.
A ordem de tentativa é Claude, Gemini, Groq e NVIDIA.

> As chaves ficam no cofre de credenciais do Windows. Se preferir, também dá pra colocá-las no
> `backend\.env` (o arquivo já foi criado, é só preencher). Se configurar dos dois jeitos, vale o que está salvo na tela.

## 5. Seu perfil e sua estratégia

Sem isso as mensagens saem genéricas. São dois minutos que mudam a qualidade de tudo.

**Seu perfil** (Configurações > Seu perfil): seu nome, o que você faz em uma frase e, se quiser, seu diferencial.
As mensagens saem assinadas por você.

**Sua estratégia de abordagem** (Configurações > Estratégia de abordagem):

1. Clique em **Começar pelo modelo**.
2. Troque cada trecho marcado com `[PREENCHER: ...]` pelo seu: nome, empresa, o que você vende e a dor que resolve.
3. Salve. O botão só libera quando não sobrar nenhum `[PREENCHER]`.

Escreva do jeito que explicaria pra alguém novo no seu time. Vale a partir da próxima mensagem gerada, sem reiniciar nada.
Se deixar vazio, o sistema usa um padrão simples (oferta de site).

## 6. Primeira busca

1. Vá em **Leads** e clique em **Nova busca**.
2. Escolha **por texto** (ex.: `clínica de estética em Londrina`, um por linha) ou **por mapa**
   (solte pinos, ajuste o raio e marque os nichos).
3. Clique em buscar e acompanhe o andamento na tela.

Cada negócio encontrado é analisado (site, reputação) e recebe uma **nota de 0 a 100**. Como ponto de partida:

| Nota | Sugestão |
|---|---|
| 70 ou mais | Abordagem manual e personalizada (vale o seu tempo) |
| 40 a 69 | Bom para campanha em lote |
| Menos de 40 | Não vale o esforço |

Dá pra mudar os pesos da nota em `backend\pesos_score.json` (por exemplo, dar bônus a um nicho com `nichos_alvo`).

Também dá pra **importar uma lista** (CSV ou "Nome, telefone" por linha) na tela Leads.

## 7. Primeira mensagem

1. Abra a ficha de um lead (clique no cartão).
2. Veja o **Raio-X do site** e a **estratégia sugerida** para ele.
3. Clique em **Gerar copy de contato** (abordagem direta) ou **Gerar pedido de print** (abertura que não vende nada, só pede
   pra falar com o responsável). Edite o texto se quiser.
4. Copie e envie. Com o WhatsApp integrado, envie direto pelo botão da ficha.
5. Marque o status e, se quiser, um follow-up. O sistema agenda um follow-up 3 dias depois do contato.

Dica: **Ctrl+K** abre a busca global (pula pra qualquer tela ou acha um lead pelo nome).

## 8. WhatsApp integrado (opcional)

Com ele você envia pelo sistema, vê as respostas dentro da ficha do lead e pode rodar campanhas em lote.

**Antes de tudo, leia isto:** automatizar WhatsApp vai contra os termos da Meta e **o número pode ser banido**. Use um
**chip separado do seu número oficial**.

1. Abra o Docker Desktop e espere aparecer **Engine running**.
2. Abra o `iniciar.bat` (ele sobe a Evolution API sozinho).
3. No sistema, vá em **WhatsApp**, clique em **Conectar WhatsApp** e **leia o QR code** com o WhatsApp do chip de prospecção
   (WhatsApp > Aparelhos conectados).
4. Proteja o seu número principal: no `backend\.env`, descomente e preencha `NUMERO_OFICIAL=` com ele. Se esse número
   for o conectado, o sistema **recusa campanha**.
5. Chip novo começa devagar: o **aquecimento** limita o dia 1 a 15 envios e sobe 5 por dia sem falha, até 150.

Detalhes e regras de segurança em [whatsapp/README.md](../whatsapp/README.md).

**Campanhas** (menu Campanhas): escolha os filtros, escreva ou escolha um template pronto, veja a prévia e inicie.
Os templates prontos trazem `[PREENCHER: ...]` para você trocar pelo seu nome e empresa; a campanha recusa texto que ainda os tenha.
Primeiro contato **sem link**, sempre.

## 9. A rotina do dia a dia

1. Abra o sistema e vá em **Hoje**.
2. Os follow-ups vencidos vêm primeiro; depois os leads novos mais quentes.
3. **Enter** envia, **seta pra direita** pula, **Backspace** ignora.
4. Responda os leads que escreveram (a conversa aparece na ficha).
5. De vez em quando, rode uma busca nova ou uma campanha em lote.

---

## Problemas comuns

**A tela não abre / "não é possível acessar o site".**
Espere uns 10 segundos depois do `iniciar.bat` e recarregue. Se persistir, veja `logs\frontend-erro.log` e `logs\backend-erro.log`.

**"Python não encontrado" ou "Node.js não encontrado".**
Instale (passo 1) e, no Python, marque *Add python.exe to PATH*. Feche e abra o `iniciar.bat` de novo.

**A porta 5000 ou 5173 já está em uso.**
Feche o que estiver usando (ou outra cópia do PROSPECT WITH MICO) e rode o `iniciar.bat` de novo.

**A busca não acha nada ou dá erro de chave.**
Confira a chave do Google Places (passo 3), se a **Places API (New)** está ativada e se o faturamento do projeto está ativo.
A mensagem de erro na tela diz o motivo; os detalhes técnicos ficam em `backend\logs\prospeccao.log`.

**A mensagem não é gerada.**
Confira se há pelo menos uma chave de IA configurada e se a cota dela não acabou (passo 4).

**O WhatsApp não conecta.**
O Docker Desktop precisa estar aberto e com **Engine running**. Veja `whatsapp\README.md`. O QR code expira: gere outro.

**Quero apagar tudo e recomeçar.**
Feche o sistema, apague `backend\leads.db` e abra de novo. Há backups automáticos em `backend\backups\`.

**Como faço backup?**
Copie `backend\leads.db` (seus leads) e `backend\estrategia_abordagem.md` (sua estratégia).
