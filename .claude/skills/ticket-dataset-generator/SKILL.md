---
name: ticket-dataset-generator
description: 'Gera datasets sintéticos de tickets de help desk/suporte (ou dados tabulares similares rotulados por categoria) em lotes, evitando a homogeneidade textual (Self-BLEU alto) que torna um dataset artificialmente fácil de classificar e enfraquece a validade de experimentos de classificação de texto. Use sempre que o usuário pedir para gerar, criar, aumentar, expandir ou continuar um dataset de tickets, chamados, e-mails de suporte, ou qualquer dataset sintético de texto rotulado por categoria — mesmo em frases curtas/informais como "gera mais tickets", "continua o dataset", "preciso de mais dados pro TCC", "aumenta esse dataset de chamados". Cobre: schema e categorias, geração em dois estilos (zero-shot formal variado / few-shot casual guiado por exemplos reais), lotes com numeração contínua de ticket_id, e consolidação com verificação de duplicatas e balanceamento por categoria.'
---

# Gerador de dataset sintético de tickets

## Por que isso não é um script

Dá pra imaginar um script que gera "tickets" combinando um dicionário de
sintomas com um dicionário de categorias. O problema: isso produz exatamente
o tipo de dataset homogêneo e artificialmente fácil de classificar que
estudos sobre dados sintéticos (e TCCs de classificação de texto que usam
esse tipo de dataset) identificam como uma ameaça séria à validade do
experimento — um classificador treinado nesses dados aprende atalhos
lexicais superficiais em vez de representações semânticas reais, e isso só
aparece quando alguém mede a diversidade textual (Self-BLEU, Distinct-n) ou
tenta aplicar o modelo a dados reais.

Por isso a geração do **texto de cada ticket é sempre feita por você**
(o modelo), nunca por um script de template. O script bundled
(`scripts/batch_tools.py`) cuida só da parte mecânica — numerar, consolidar,
checar duplicatas — que não tem valor em ser "criativa" e só desperdiça
esforço se for refeita à mão a cada lote.

## Passo 1 — Definir schema, categorias e domínio

Se o usuário está continuando um projeto existente, procure os arquivos de
lote já gerados (ex: `data/raw/**/lote*.csv`) e leia o cabeçalho para
descobrir o schema em uso — não pergunte algo que já está nos arquivos.

Se for um projeto novo, pergunte (ou proponha um default e confirme):
- Quais colunas o dataset precisa ter (schema)
- Quantas categorias, e quais
- Um domínio fictício para os e-mails (nunca use domínios ou nomes de
  empresas reais)

`references/exemplo-tcc-tickets.md` tem um exemplo completo e já validado
(6 categorias de help desk, schema de 7 colunas, domínio fictício) — use como
modelo quando fizer sentido, inclusive para continuar aquele projeto
especificamente.

## Passo 2 — Escolher o(s) estilo(s) de geração

Pergunte ao usuário (ou infira do contexto) se ele quer:
- **Zero-shot**: você define o estilo sozinho, sem exemplos reais como
  referência. Varie deliberadamente o tom dentro de cada categoria —
  neutro, frustrado, formal, em dúvida, tecnicamente detalhado — porque tom
  constante é uma das formas mais fáceis de um dataset ficar homogêneo.
- **Few-shot**: o usuário te dá (ou já existem no projeto) exemplos reais de
  tickets, e você gera novos seguindo o registro observado nesses exemplos
  (formalidade, erros de digitação naturais, uso de minúsculas, gírias).
  Isso tende a produzir texto mais parecido com dados reais do que
  zero-shot puro.
- **Os dois**, quando o objetivo é comparar diversidade/desempenho entre as
  duas abordagens (nesse caso, gere os dois como arquivos separados).

## Passo 3 — Gerar um lote

**Tamanho de lote recomendado: 10 tickets por categoria por estilo.** Isso
dá um lote de 60 (um estilo) ou 120 (dois estilos) por vez — grande o
suficiente para progredir rápido, pequeno o suficiente para você manter
qualidade e variedade real em vez de começar a repetir frases ou estruturas
no fim do lote. Se o usuário pedir um volume muito maior que isso de uma vez
(centenas ou milhares), explique que gerar em lotes menores preserva a
qualidade e pergunte se ele quer continuar lote a lote ao longo de várias
mensagens, em vez de prometer um volume grande que sairia repetitivo.

Antes de escrever o lote, rode para saber o próximo `ticket_id` livre e o
que já foi usado:

```bash
python scripts/batch_tools.py status --inputs caminho/lote*.csv
```

(se não houver lotes anteriores, comece do ticket_id 1 e pule esse passo)

Ao escrever o conteúdo de cada ticket, varie deliberadamente, não só o tom:
- **Dispositivo/sistema específico** dentro da categoria (um ticket de
  Hardware não precisa ser sempre sobre notebook — mouse, impressora,
  monitor, headset, leitor de crachá, estabilizador...)
- **Perfil do remetente** (cargo, urgência, nível técnico)
- **Estrutura da frase** (nem todo ticket "formal" precisa começar com
  "Prezados" — varie aberturas, comprimento, nível de detalhe)
- **Nomes e domínios de e-mail**, sempre únicos — nunca repita um nome ou
  e-mail já usado em um lote anterior do mesmo dataset. Varie também o
  **padrão** do endereço (`nome.sobrenome`, `inicial+sobrenome`,
  `sobrenome.nome`, `nome_sobrenome`, com número no fim etc.): usar
  `nome.sobrenome@dominio` em todos é uniforme demais

Monte os tickets do lote como uma lista de objetos JSON (sem `ticket_id` —
o script atribui isso):

```json
[
  {
    "nome_remetente": "Nome Completo Fictício",
    "email_remetente": "nome.sobrenome@dominio-ficticio.com.br",
    "categoria": "NomeDaCategoria",
    "assunto_email": "assunto do ticket",
    "corpo_email": "corpo do ticket, no registro apropriado ao estilo escolhido",
    "data_envio": "YYYY-MM-DD"
  }
]
```

Salve essa lista em um arquivo `.json` temporário e escreva o CSV do lote:

```bash
python scripts/batch_tools.py write --data lote_tmp.json --out loteN_<estilo>.csv --start-id <próximo id livre>
```

## Passo 4 — Consolidar e verificar

Depois de escrever (ou atualizar) os lotes de um estilo, consolide tudo em
um único arquivo e deixe o script confirmar que não há duplicatas e que as
categorias continuam balanceadas:

```bash
python scripts/batch_tools.py consolidate --inputs lote1_<estilo>.csv lote2_<estilo>.csv ... --out dataset_consolidado_<estilo>.csv
```

Se o script apontar duplicatas de e-mail ou de texto (assunto+corpo), **não
ignore o aviso** — ou troque o nome/e-mail colidente, ou reescreva o ticket
duplicado antes de considerar o lote pronto.

## Passo 5 — Medir diversidade (Self-BLEU e Distinct-n)

Depois de consolidar, meça a diversidade textual de cada estilo. Esse é o
passo que confirma, com números, que o dataset não ficou homogêneo — algo que
a checagem de duplicatas do Passo 4 não detecta (textos podem ser todos
diferentes e ainda assim muito parecidos entre si).

```bash
python scripts/diversity.py --inputs zero-shot=dataset_consolidado_zero_shot.csv few-shot=dataset_consolidado_few_shot.csv
```

Por padrão usa só `corpo_email`; para incluir o assunto, acrescente
`--fields assunto_email corpo_email`. Com um único estilo, passe só um
`rotulo=caminho.csv`. O script reporta, por conjunto e por categoria:
- **Self-BLEU-2/3/4**: quanto **menor**, mais diverso
- **Distinct-1/2/3**: quanto **maior**, mais diverso

A tokenização ignora maiúsculas e acentos ("não" e "nao" contam como a mesma
palavra), para a comparação entre estilo formal e casual não ser distorcida.

Ao reportar os números ao usuário, inclua os cuidados de interpretação:
- Com poucas centenas de tickets, diferenças pequenas **não são
  significativas**; não declare um estilo "melhor" sem corpus maior.
- Self-BLEU por categoria usa menos referências e dá valores menores que o
  global — não compare os dois diretamente.
- Textos mais curtos (comuns no few-shot casual) tendem a ter Distinct-n menor.
- A implementação é própria; para citar em trabalho acadêmico, vale conferir
  com `--check-nltk` (requer `pip install nltk`).

Se o Self-BLEU subir de um lote para o outro, é sinal de que a geração está
começando a repetir estruturas: reescreva os tickets mais parecidos ou varie
mais dispositivos, perfis e aberturas no próximo lote.

## Passo 6 — Reportar progresso

Sempre que o usuário tiver uma meta de volume (ex: replicar a escala de um
dataset de referência), termine informando, de forma direta:
- quantos tickets existem agora, por estilo
- quanto falta para a meta
- quantos lotes nesse ritmo ainda são necessários

Isso evita prometer implicitamente "terminei" quando só uma fração da meta
foi atingida, e ajuda o usuário a decidir se quer continuar agora, pausar,
ou ajustar a meta.

## Formato de saída

Por padrão, gere o arquivo como `.csv` (é o formato que os prompts de
geração de dados sintéticos tipicamente pedem, e o que ferramentas de
treino como pandas/HuggingFace Datasets leem nativamente). Se o usuário
pedir `.xlsx` especificamente, gere o CSV normalmente e só então converta
com `pandas` (`pd.read_csv(...).to_excel(...)`) — mais simples e menos
propenso a erro do que escrever xlsx diretamente.
