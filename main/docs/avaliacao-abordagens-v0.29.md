# Avaliação das sugestões — 0.29

O anexo foi comparado com o código da 0.28. Nenhuma abordagem foi tratada como imune a basslines. Esta rodada prioriza medir a restrição real e acrescentar evidência sem criar kicks pela grade ou relaxar globalmente a identificação.

| Sugestão | Decisão |
|---|---|
| P6 · Replay causal com rótulos | Implementado primeiro, com WAV PCM em streaming, relatório visual/JSON, erro de timestamp, latência de disponibilidade, falsos/minuto, confusão de estados e rastreio por etapa. Rótulos não entram na análise. |
| A5 · Clique 2–6 kHz | Implementado como canal auxiliar no FFT estrutural já existente, com quatro sub-bandas e envelope causal. Precisa de quatro referências com clique no groove, coincidência temporal e forma compatível. Não propõe um kick sozinho. |
| A5 · Retirar fundo harmônico | Já há novidade por bin, branqueamento causal e transiente/cauda com fundo subtraído. Foram preservados. Não foi adicionado outro separador em paralelo nesta rodada. |
| A1 · Impacto versus continuidade | A fase `impact` e a confirmação posterior por três kicks já existem. O novo apoio permite passar pela identidade curta em vez da espera longa quando há evidência suficiente. O primeiro flash continua associado a um kick real; a contagem pós-drop permanece em oito kicks confirmados. |
| A2 / P1 / P3 · Degrau, change-point e novidade sem kick | As 12 bandas e a novidade já são calculadas. Não viraram gatilho independente de drop: prato, baixo percussivo e entrada de synth podem produzir mudanças semelhantes. Primeiro é necessário medir esses negativos em faixas reais. |
| A3 / P2 · Prior 8/16/32 e HSMM | Não foi usado para baixar limiares. O início da frase é relativo; loops e mixagens podem contrariar a duração presumida. Acrescentar uma distribuição sem dados rotulados esconderia esse erro. |
| A4 · Pausa curta | Já existe queda de 8 dB por pelo menos 60 ms e preservação breve da referência. Foi mantida; pausa não confirma um drop sem ataque compatível. |
| A5 · Sidechain | Não foi usado como prova de kick: um baixo pode ser bombeado sem bumbo audível. Exigiria medir casos negativos específicos. |
| HPSS completo | Adiado. O método clássico usa medianas temporais e espectrais; introduzir outra representação exigiria validar causalidade, máscaras e os limiares de identidade existentes. O apoio novo reutiliza o FFT e evita uma segunda cadeia de separação/reconstrução. |
| P4 · TCN/GRU/ONNX | Adiado: não há modelo treinado, conjunto real rotulado ou validação de generalização nesta entrega. Nenhuma dependência de inferência foi adicionada. |
| P5 · Pré-análise/fingerprint da biblioteca | Adiado: exigiria resolver posição do deck, mudanças de pitch e loops; o sistema atual recebe uma mixagem por áudio. |

O HPSS por medianas é descrito por [FitzGerald, DAFx 2010](https://dafx.de/paper-archive/2010/DAFx10/DerryFitzGerald_DAFx10_P15.pdf). A decisão de não inseri-lo agora decorre dos riscos de integração e da falta de validação no repertório do usuário, não de uma alegação de que toda implementação teria custo alto.

## Exceção conservadora no retorno

O replay encontrou um caso no qual forma grave, queda curta e harmônicos passavam, mas o contraste da MIXAGEM era inferior a 1,5 dB devido ao baixo contínuo. O novo caminho permite contraste a partir de 0,35 dB somente com clique previamente aprendido e coincidente, similaridade de clique ≥0,90, amplitude relativa compatível e potência do transiente grave **≥125% da referência**. A margem adicional foi necessária para rejeitar um roll fraco que produzia estimativa de potência ambígua sob baixo.

Forma e queda do grave, harmônicos, grade, contexto de retorno e verificações posteriores de potência continuam obrigatórios. Os limiares globais de 70%/85% não foram reduzidos. O novo caminho não aprende a referência nem corrige a fase. Clique não aprendido, tardio, prato/crash isolado e baixo sem kick não liberam essa exceção nos testes.

Ao voltar ao groove depois dos oito kicks, a mesma evidência conservadora pode manter o reconhecimento do corpo mascarado. Nesse contexto ela é aplicada após a janela longa, com alinhamento obrigatório e sem reaprender a referência. Assim o fim da cena de drop não interrompe a identificação dos kicks seguintes.

A confirmação curta observa cerca de 55 ms depois do candidato, mais a janela FFT e disponibilidade do bloco. Não há promessa de latência zero. O modo completo de 120 ms continua como fallback; não basta aumentar sensibilidade ou arredondar timestamps.

O clique pode preceder o corpo filtrado em cerca de 30 ms; uma janela de coincidência de −45 a +25 ms respeita essa diferença sem deslocar os eventos da grade. O envelope também trata o caso em que o fluxo cruzou o limiar ainda abaixo do piso audível. Tudo usa somente frames já recebidos.

Veja [replay e métricas](replay-causal.md) e [validação da entrega](validacao.md). Sem as gravações problemáticas e seus rótulos, a melhora demonstrada continua limitada aos casos sintéticos descritos.
