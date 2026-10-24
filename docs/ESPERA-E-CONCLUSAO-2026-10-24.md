# Espera útil e conclusão das análises — 24/10

Revisão posterior a `3695031`. Correções locais de prazo/encerramento; não são nova medição de acerto nem publicação em produção.

## O que estava acontecendo

A interface já usava `await`: não abria o relatório antes da resposta nem terminava a análise por causa de uma animação. Os 400 ms visuais ocorrem depois da resposta.

Havia um descompasso concreto no planejador de buscas: a espera externa podia ser de 45 s, mas a chamada OpenRouter não recebia esse orçamento e conservava seu padrão interno de 25 s. Esperar mais no navegador não eliminava esse corte no servidor.

Outro defeito apareceu nos testes de timeout: o cliente OpenRouter tinha um prazo externo e outro praticamente coincidente na última tentativa. Dois cancelamentos podiam interromper a limpeza assíncrona do transporte. O controle inicialmente falhou em 11 de 40 repetições. Gemini tinha estrutura equivalente, embora aquelas 40 repetições não tivessem mostrado falha nele. Ambos agora mantêm somente o prazo externo na última tentativa; a fatia interna continua existindo quando há uma alternativa explicitamente configurada.

Esses achados não provam que todo inconclusivo anterior veio de timeout. Na última amostra, 13 de 14 inconclusivos ocorreram antes da comparação dos modelos, principalmente por descoberta/seleção insuficiente. [Diagnóstico da queda](CAUSA-QUEDA-E-RECUPERACAO-2026-10-24.md).

## Novos limites

São tetos, não pausas obrigatórias. A análise segue imediatamente quando recebe uma resposta completa e válida. Etapas compartilham o tempo restante, sem somar novos prazos integrais após uma falha.

| Etapa | Antes | Agora |
| --- | --- | --- |
| Análise textual, incluindo extração | 330 s | 420 s |
| Consultas paralelas e recuperação | 110 s | 150 s |
| Recuperação com pesquisa assistida | 105 s | 145 s |
| Planejador de buscas | 45 s, chamada OpenRouter implícita de 25 s | até 60 s, prazo explícito igual no transporte e na espera |
| Reserva após o planejamento para buscar/ler | 20 s | 30 s |
| Comparação documental compartilhada | até 180 s | até 240 s |
| Cada provedor da comparação | até 90 s | até 120 s, limitado ao restante |
| Navegador: texto/link/lote/texto conferido | 360 s | 480 s |
| Navegador: upload/áudio/vídeo | 360 s | 360 s, inalterado |

`analysis_timing.py` centraliza os tetos do backend. Texto e link têm margem no cliente: 480 s cobrem 420 s de pipeline mais até 20 s de consulta inicial do link e 40 s para outras fronteiras. Essa margem não é garantia contra proxies, desconexões, filas ou persistência lentos; a limpeza de I/O cancelado continua sendo aguardada.

O limite explícito dos clientes Gemini/OpenRouter aceita até 120 s. Os padrões gerais anteriores continuam iguais: Gemini 60 s, configurável de 10 a 90 para extração/OCR; OpenRouter 25 s para chamadas que não passam prazo. Comparação e planejamento passam seus próprios limites explicitamente. Não houve aumento automático dos detectores pagos, duração/quantidade de mídia ou quotas por provedor.

## Esperar confirmação, sem fabricar consenso

- Pesquisa aguarda um plano válido antes de executar suas consultas. Contexto e schema consomem o mesmo prazo original.
- Leitura concluída precede a comparação. A comparação precede a decisão/relatório.
- Uma resposta HTTP bem-sucedida não basta: a comparação exige a revisão completa dos pares afirmação/fonte e citações válidas.
- Resposta válida, inclusive insuficiente, encerra aquela avaliação. Não se consulta outro modelo para conseguir o veredito desejado.
- A alternativa usa somente o tempo não gasto e somente no caminho de indisponibilidade previsto. Não exige duas IAs simultâneas nem trata concordância como evidência independente.
- Ao esgotar o prazo, operações pendentes são canceladas e encerradas antes de prosseguir. Respostas incompletas não são usadas como confirmação.
- Detalhes técnicos registram limite de espera e tempo efetivamente gasto, sem respostas brutas, chaves ou percentual fictício de progresso.

## Configuração existente

Nenhum `.env` privado ou variável remota foi lido/alterado nesta revisão. O exemplo versionado foi atualizado.

Se Railway ou seu `.env` privado já tiverem o valor antigo, ele continua prevalecendo. Para usar a janela ampliada da comparação, ajustar **somente**:

```dotenv
SOURCE_CROSSCHECK_TIMEOUT_SECONDS=240
```

Reiniciar o backend local, ou implantar esta revisão e aplicar a variável no Railway. `180` continua válido, mas mantém o limite anterior. Não copiar o arquivo de exemplo inteiro sobre variáveis existentes, não substituir chaves por valores vazios e não aumentar créditos/limites para acompanhar a espera.

Para testar uma compilação local, `VITE_API_URL` deve apontar para o backend local ou ficar vazio para usar `/api` com proxy/origem adequados. Uma URL pública antiga no ambiente de build faz o navegador chamar esse serviço, mesmo que o frontend esteja aberto em localhost. O controle desta rodada encontrou esse endereço herdado; uma nova compilação de teste usou override vazio, sem editar o arquivo privado.

## Validação e limites

- 1.493 testes backend passaram, sem rede, credenciais privadas, HTTP real ou skips no runner offline. São 24 novos controles de espera nesta revisão, além da atualização das regressões de prazo existentes.
- 205 testes frontend passaram e o build de produção compilou (1.977 módulos).
- Eventos assíncronos comprovam que páginas pendentes impedem comparação, comparação pendente impede relatório e respostas tardias dentro do novo orçamento não são descartadas. Tempos são escalados para não aguardar minutos na suíte.
- Controles verificam janela de 120 s/recusa de 121 s, invalidade de NaN/infinito/inteiros enormes, cancelamento, ausência de duplicação de envio e alternativa recebendo apenas o restante.
- Regressões determinísticas conferem um único temporizador na última tentativa, limpeza concluída antes do retorno, modelos/payload e reserva normal por envio. Repetições curtas complementares passaram após a correção; não são amostras de acerto factual.
- No navegador foi observado o estado pendente com botão desabilitado e aviso acessível. A primeira submissão usou a URL pública herdada e falhou na conexão. Após corrigir a compilação local e reiniciar o controle, a reabertura foi interrompida pelo navegador; não houve contorno de proteção. **O caminho visual completo até o relatório continua pendente.**
- O atraso de 25 s existia somente no controle descartável de UI, nunca no código da aplicação. Não foi usado para simular uma resposta de IA real ou contabilizado como precisão.

Nenhuma nova rodada remota de vereditos foi concluída, nem mídia revalidada. O orçamento OpenRouter da rodada anterior permanece esgotado; não foi reposto. Última medição real: 6/12 conhecidos corretos (50%), 0/8 novos, 14/20 inconclusivos e nenhuma conclusão errada observada naquela amostra. Os testes desta revisão não autorizam substituir esses números ou anunciar 80%.

Próxima medição deve congelar o código e separar os controles já conhecidos de novos assuntos, mantendo inconclusivos no denominador. Continuam pendentes a recuperação de fontes ausentes, correspondência semântica conservadora e avaliação real de cada modalidade; mais tempo não resolve sozinho fonte errada, falta de acesso, rota 404 ou quota esgotada.
