# ClaimReview, análise semântica e preservação de trechos literais

## Papel atual no resultado

ClaimReview não é mais a camada decisória única. O relatório textual principal usa Gemini para interpretar semanticamente as notícias e páginas recuperadas. Cada afirmação recebe uma relação por fonte:

- `supports`: a fonte apoia a afirmação;
- `contradicts`: a fonte contradiz a afirmação;
- `context_only`: a fonte trata do assunto, mas não resolve a afirmação;
- `insufficient`: material insuficiente.

O relatório mostra URL, título, trecho literal validado e limitações. A interpretação não é certeza nem probabilidade matemática. Google Fact Check aparece em `editorial_complement` como referência adicional e nunca decide sozinho.

## ClaimReview na prática

ClaimReview é uma **checagem já publicada por algum veículo especializado**.

Exemplo:

Usuário envia:

> “Vacina X causa autismo.”

Google Fact Check pode retornar:

```json
{
  "claim_text": "Vacina X causa autismo.",
  "rating": "Falso",
  "publisher": "Aos Fatos",
  "url": "https://...",
  "review_date": "2026-..."
}
```

`claim_policy.py` compara afirmação do usuário com `claim_text` para preservar compatibilidade e apresentar o complemento editorial.

- Correspondência exata + rating explícito → evidência editorial complementar.
- ClaimReview sobre frase diferente → ignorado.
- Sem ClaimReview correspondente → análise semântica continua possível com outras fontes.

O Verify não decide que vacina causa ou não causa algo por conhecimento próprio. Ele reproduz, com filtros, classificação editorial publicada.

## Source attribution na prática

Sim. `source_attribution.py` procura se uma página pública contém **literalmente** trecho correspondente ao texto do usuário.

Fluxo:

1. Texto do usuário vira consultas literais.
2. Serper encontra páginas candidatas.
3. Verify acessa essas páginas.
4. Extrai texto visível do corpo.
5. Procura frase literal completa.
6. Guarda URL, título e trecho encontrado.

Exemplo:

Usuário:

> “Elizabeth II morreu em 8 de setembro de 2022.”

Página contém exatamente:

> “Elizabeth II morreu em 8 de setembro de 2022.”

Resultado:

```json
{
  "url": "https://example.com",
  "claim": "Elizabeth II morreu em 8 de setembro de 2022.",
  "excerpt": "Elizabeth II morreu em 8 de setembro de 2022.",
  "source_role": "retrieved_reference"
}
```

Isso prova apenas:

> “Essa frase apareceu nessa página.”

Não prova que a frase é verdadeira. A página pode estar citando, negando ou reproduzindo um boato.

Também não precisa ser notícia: pode ser página oficial, artigo, documento público ou link enviado pelo usuário. Snippet, título ou frase parecida não bastam.
