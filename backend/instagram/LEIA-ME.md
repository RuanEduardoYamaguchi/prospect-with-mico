# Prospecção via comentários do Instagram

> **Módulo experimental, sem tela no sistema.** Os scripts desta pasta rodam
> pelo terminal e automatizam uma conta pessoal do Instagram, o que pode
> resultar em checkpoint ou banimento da conta. Se for usar, use uma conta
> secundária, com moderação, e nunca compartilhe o arquivo de sessão gerado.
> O fluxo principal do PROSPECT WITH MICO é Google Maps → WhatsApp.

Canal complementar ao scraper do Google Maps: em vez de raspar listagens
passivas, aqui a gente raspa comentários de posts em nichos-alvo (ex.: um
vídeo direcionado a advogados) para achar gente que comentou demonstrando
interesse ou se identificando como dono de negócio.

## Como funciona

1. **`login.py`** — faz login uma vez e salva a sessão.
2. **`raspar_comentarios.py`** — recebe a URL de um post e extrai todos os
   comentários (username + texto). Passo rápido e leve.
3. **`enriquecer_perfis.py`** — recebe o JSON gerado no passo anterior e,
   para cada autor único, busca se o perfil é público, a bio e o número de
   seguidores. Passo mais lento e mais arriscado para a conta — use com
   moderação.
4. Cole o JSON enriquecido numa IA (Claude, por exemplo) e peça pra filtrar e
   ranquear os melhores leads.

## Nota técnica

A primeira versão desta pasta usava a biblioteca `instaloader`, mas o
Instagram descontinuou a consulta GraphQL que ela usa para buscar posts
(erro `"Fetching Post metadata failed"`, problema conhecido e ainda sem
correção — [issues abertas no GitHub oficial](https://github.com/instaloader/instaloader/issues)).
Migramos para `instagrapi`, que usa a API privada mobile do Instagram (mais
estável nesse ponto) e está ativamente mantida.

## Configuração inicial (só precisa fazer uma vez)

```powershell
py instagram\login.py SEU_USUARIO
```

Isso vai pedir sua senha (não aparece nada na tela ao digitar, é normal) e,
se o Instagram pedir, um código de verificação (2FA) — o próprio script
pergunta na hora. Ao final, salva a sessão em `instagram/sessao/session-SEU_USUARIO.json`.

Se em algum momento os outros scripts reclamarem de sessão expirada, é só
rodar esse login de novo.

## Uso do dia a dia

```powershell
# 1. Extrair comentários de um post
py instagram\raspar_comentarios.py https://www.instagram.com/p/XXXXXXXXX/

# 2. Enriquecer os perfis que comentaram (público/privado, bio, seguidores)
py instagram\enriquecer_perfis.py instagram\comentarios\post_123456789_20260707_103000.json
```

Os arquivos gerados ficam em `instagram/comentarios/` (não vão pro git).

## Cuidados importantes

- **Use sua conta pessoal com moderação.** Rodar isso o dia todo em loop é
  o que mais aumenta o risco de checkpoint/banimento. Trate como uma
  ferramenta de uso pontual, não de scraping em massa.
- **`enriquecer_perfis.py` é o passo mais arriscado** — ele faz uma consulta
  extra por autor único que comentou. Prefira rodá-lo só depois de já ter
  olhado os comentários brutos e descartado manualmente o que é óbvio spam.
- Perfis com `is_private: true` não podem receber DM — são descartados
  automaticamente na etapa de análise com o Claude.
