# WhatsApp (Evolution API)

Esta pasta sobe a **Evolution API**, a ponte entre o PROSPECT WITH MICO e o WhatsApp, em Docker.
É opcional: sem ela o PROSPECT WITH MICO funciona normalmente, só não envia nem recebe mensagens pelo sistema.

## Como subir

Com o Docker Desktop aberto (**Engine running**), o `iniciar.bat` da raiz já sobe tudo.
Pra subir só o WhatsApp, dentro desta pasta:

```powershell
docker compose up -d
```

Antes da primeira vez, rode o `configurar.bat` da raiz: ele cria o `whatsapp\.env` com a chave da API e a
senha do banco **geradas aleatoriamente na sua máquina**. Não copie o `.env.example` na mão.

## Conectar o número

1. No PROSPECT WITH MICO, abra **WhatsApp** e clique em conectar. Aparece um QR code.
2. No celular do **chip de prospecção**: WhatsApp > Aparelhos conectados > Conectar um aparelho > leia o QR code.
3. O QR code expira em pouco tempo. Se vencer, gere outro.

## Segurança

- A Evolution escuta **só em `127.0.0.1:8080`** (o seu computador). Nada fica exposto na rede.
- O Postgres e o Redis **não têm porta publicada**: só a Evolution fala com eles.
- A chave da API fica no `whatsapp\.env` (fora do Git). Não compartilhe esse arquivo.
- As respostas dos leads chegam ao PROSPECT WITH MICO por um webhook local (`host.docker.internal:5000`).

## Cuidado com o número

Automatizar o WhatsApp vai contra os termos da Meta. **O número pode ser bloqueado.**

- Use um **chip separado** do número oficial do seu negócio. Defina `NUMERO_OFICIAL` no `backend\.env` e o sistema
  recusa campanha nele.
- Chip novo começa com volume baixo. O **aquecimento** limita o dia 1 a 15 envios e sobe 5 por dia sem falha, até 150.
  Um dia com 5 ou mais falhas não sobe o teto do dia seguinte.
- **Sem link no primeiro contato.** É o que mais gera denúncia.
- Quem diz "não tenho interesse" ou pede pra sair é removido de todas as campanhas automaticamente.
- Mande para quem tem relação comercial plausível com o que você oferece, e identifique-se logo na primeira mensagem.

## Comandos úteis

```powershell
docker compose ps                      # o que está rodando
docker compose logs -f evolution-api   # logs da Evolution
docker compose down                    # para tudo (os dados ficam guardados)
docker compose down -v                 # para e APAGA a conexão do WhatsApp e o banco da Evolution
```
