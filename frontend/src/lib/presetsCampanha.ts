/** Templates prontos de primeiro contato. Só os sem link entram aqui - link é pro
 * segundo contato, depois que a pessoa respondeu.
 *
 * Os trechos [PREENCHER: ...] precisam ser trocados antes de disparar: a campanha
 * recusa texto que ainda tem o marcador. */
export interface PresetCampanha {
  titulo: string
  texto: string
}

export const PRESETS_CAMPANHA: PresetCampanha[] = [
  {
    titulo: "Pergunta de processo (abertura leve)",
    texto: `{Oi|Olá|Bom dia}, tudo bem? Aqui é o [PREENCHER: seu nome], da [PREENCHER: sua empresa].

{Vi a {{nome}} aqui em {{cidade}}|Encontrei a {{nome}} procurando {{nicho}} em {{cidade}}} e fiquei com uma dúvida: {como vocês fazem pra novos clientes encontrarem vocês hoje|de onde vêm a maioria dos clientes de vocês hoje}?

{Posso te explicar em 2 minutos o que eu faço por negócios como o seu?|Faz sentido eu te mostrar como funciona?}`,
  },
  {
    titulo: "Oferta direta (diga o que você faz)",
    texto: `{Oi|Olá}, {{nome}}! [PREENCHER: seu nome], da [PREENCHER: sua empresa].

[PREENCHER: o que você faz por negócios como o dele, numa frase falada, falando da dor e não da tecnologia].

{Queria entender como vocês fazem isso hoje|Como isso funciona aí hoje}, é feito na mão?`,
  },
  {
    titulo: "Quem pesquisa não acha (visibilidade)",
    texto: `{Oi|Olá|Bom dia}! Aqui é o [PREENCHER: seu nome], da [PREENCHER: sua empresa].

{Pesquisei {{nicho}} em {{cidade}} no Google|Procurei {{nicho}} em {{cidade}}} e a {{nome}} {aparece bem abaixo|não aparece nas primeiras opções}. Quem está procurando não rola a página, escolhe quem aparece primeiro.

{Posso te mandar o que dá pra ajustar?|Quer que eu te mostre o que está faltando?}`,
  },
  {
    titulo: "Sem site (usar com o filtro \"sem site\")",
    texto: `{Oi|Olá}! Aqui é o [PREENCHER: seu nome], da [PREENCHER: sua empresa].

{Achei a {{nome}} no Google|Vi a {{nome}} procurando {{nicho}} em {{cidade}}} e reparei que vocês {não têm site|aparecem só no Maps}. Quem pesquisa hoje quer ver foto, preço e horário antes de chamar.

{Posso te mostrar como ficaria?|Quer ver um exemplo do que eu faço?}`,
  },
]

/** Variáveis aceitas pelo backend no template da campanha. */
export const VARIAVEIS_TEMPLATE = [
  "{{nome}}",
  "{{primeiro_nome}}",
  "{{nicho}}",
  "{{cidade}}",
  "{{nota}}",
  "{{avaliacoes}}",
] as const

/** Padrões que indicam link no texto - o backend recusa (400) template com link. */
const PADROES_LINK = [/https?:\/\//i, /www\./i, /\.com/i, /\.br/i, /wa\.me/i]

export function templateTemLink(texto: string): boolean {
  return PADROES_LINK.some((padrao) => padrao.test(texto))
}

/** Os modelos prontos trazem "[PREENCHER: ...]" nos trechos que a pessoa precisa
 * trocar. O backend recusa (400) campanha com o marcador ainda no texto. */
export function templateTemMarcador(texto: string): boolean {
  return texto.includes("[PREENCHER")
}
