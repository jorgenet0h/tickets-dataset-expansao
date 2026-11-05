# Exemplo de referência: dataset de tickets de help desk (TCC)

Este é um exemplo concreto e já validado de uso desta skill, vindo de um
projeto real (extensão de um TCC sobre classificação de tickets de help desk
com datasets sintéticos gerados por LLM). Use como ponto de partida quando o
usuário estiver continuando esse projeto especificamente, ou como modelo para
adaptar a um projeto novo.

## Schema

```
ticket_id, nome_remetente, email_remetente, categoria, assunto_email, corpo_email, data_envio
```

- `ticket_id`: inteiro sequencial, atribuído pelo script `batch_tools.py` (nunca pelo modelo)
- `nome_remetente`: nome fictício, sem relação com pessoas reais
- `email_remetente`: `nome.sobrenome@dominio-ficticio.com.br` — nunca repetir entre lotes
- `categoria`: uma das 6 categorias abaixo
- `assunto_email` / `corpo_email`: ver estilos de geração abaixo
- `data_envio`: `YYYY-MM-DD`

## Categorias (6, balanceadas)

`Hardware`, `Acesso`, `Rede`, `Software`, `Conta/Senha`, `Solicitação`

## Domínio fictício usado

`vertexcorp.com.br` (ajuste para um domínio diferente se for um dataset
não relacionado a este projeto, para não misturar dados de projetos distintos)

## Os dois estilos usados neste projeto

**Zero-shot** — variação de tom dentro de cada categoria: neutro, frustrado,
formal, dúvida, técnico-detalhado. Frases completas, pontuação e acentuação
corretas, registro mais "e-mail corporativo".

Exemplo:
> Assunto: Monitor com manchas na tela após uso prolongado
> Corpo: Meu monitor está apresentando manchas escuras persistentes na tela
> depois de algumas horas de uso contínuo, o que está dificultando bastante a
> leitura de documentos. Isso pode indicar um defeito no painel?

**Few-shot** — guiado pelo estilo real observado em exemplos de tickets
verdadeiros (quando o usuário tiver uma amostra real para mostrar): registro
coloquial, direto, às vezes sem acentuação ou com erros de digitação naturais,
assunto em letras minúsculas.

Exemplo:
> Assunto: tela com mancha estranha aparecendo
> Corpo: apareceu uma mancha escura no meu monitor depois de um tempo ligado,
> some quando desligo mas volta depois

## Progresso deste projeto (na data em que esta skill foi criada)

360 tickets gerados até agora (180 zero-shot + 180 few-shot), em 3 lotes,
rumo a uma meta de 1400 por estilo (replicando a escala do dataset "Claude
1400" original do TCC). Os arquivos ficam em
`data/raw/claude_novo/` dentro do repositório do TCC, com `loteN_<estilo>.csv`
por lote e `dataset_claude_novo_<estilo>.csv` consolidado.

Isso é apenas o estado no momento da criação da skill — **não assuma que
continua válido**: sempre rode `batch_tools.py status` nos arquivos de lote
mais recentes para saber o progresso e o próximo `ticket_id` livre antes de
gerar mais.
