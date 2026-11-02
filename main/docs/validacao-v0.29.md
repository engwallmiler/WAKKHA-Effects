# Validação — versão 0.29.0

Registro: **2026-10-30**. Replay causal com rótulos, instrumentação opcional e clique auxiliar aprendido para kicks mascarados. Ensaios sintéticos; nenhum áudio real do usuário, COM, ESP32 ou Link nativo foi utilizado nesta rodada.

## Regressão

**814 testes Python passaram**, incluindo a regressão anterior de áudio/grade/estrutura/drops, interface, projetos e transporte, mais PCM 8/16/24 bits, rótulos inválidos, regiões parciais, WAV truncado, não sobrescrever relatórios, ausência de vazamento dos rótulos para o BPM, eventos na borda de regiões, importação dos parâmetros reais de análise e equivalência do prefixo causal. O novo apoio ao kick é testado em 44,1/48 kHz, ganho baixo, baixo forte, clique tardio/não aprendido, crash sem kick, baixo percussivo e roll fraco dobrado. [Log](resultado-pytest-v0.29.txt).

**78 testes JavaScript passaram** no motor de pixels, sem alteração dos efeitos ou do protocolo USB. [Log](resultado-pixel-js-v0.29.txt).

## Comparação por replay PCM

[validate_drop_replay.py](../scripts/validate_drop_replay.py) gera nove arranjos de 17 s, grava PCM estéreo e entrega os mesmos blocos de 512 samples ao analisador de cada versão. A 0.28 é importada do wheel preservado. Rótulos entram apenas nas métricas. A decisão usa o fim do bloco recebido, incluindo a janela FFT; não usa o centro da FFT como se a decisão já estivesse disponível.

| Cenário | 0.28 | 0.29 | Atraso disponível 0.29 |
|---|---|---|---:|
| Retorno normal | Primeiro kick, oito posições | Primeiro kick, oito posições | 85,3 ms |
| Kick sob baixo forte, clique aprendido | Drop perdido | Primeiro kick, oito posições | 96,0 ms |
| Baixo ainda mais forte | Drop perdido | Primeiro kick, oito posições | 96,0 ms |
| Roll fraco dobrado antes do drop | Drop perdido | Sem antecipação; primeiro kick real e oito posições | 96,0 ms |
| Baixo sem kick | Sem drop | Sem drop | — |
| Crash sem kick | Sem drop | Sem drop | — |
| Baixo percussivo com clique | Sem drop | Sem drop | — |
| Clique não aprendido | Drop perdido | Drop perdido; exceção bloqueada | — |
| Clique atrasado 90 ms | Drop perdido | Drop perdido; exceção bloqueada | — |

Os dois últimos casos mostram um limite intencional: a nova evidência não ajuda se não foi aprendida ou não coincide com o corpo. Não se afirma resolver todas as faixas. Houve zero falsos drops nos três negativos descritos; não é uma estimativa de taxa universal.

[Referência 0.28](resultado-replay-drop-v0.28.0.json) · [Resultado 0.29](resultado-replay-drop-v0.29.0.json) · [Log](resultado-replay-drop-v0.29.txt) · [Critérios e decisões sobre o anexo](avaliacao-abordagens-v0.29.md).

O rastreio revelou que, nos casos difíceis, forma, queda curta e harmônicos passavam, mas o contraste da MIXAGEM era inferior a 1,5 dB. O apoio novo exige clique aprendido, compatibilidade espectral, coincidência e margem adicional de potência grave. Um falso disparo num roll fraco durante o desenvolvimento motivou a margem de 125%; o teste negativo permanece na suíte. Os limiares globais não foram reduzidos.

## Custo do DSP de apresentação

[measure_dsp_cost.py](../scripts/measure_dsp_cost.py) fez três execuções por cenário de oito segundos, sem GUI, trace, hardware ou pytest simultâneo. As medianas de CPU por duração de áudio foram:

| Cenário | 0.28 · um núcleo | 0.29 · um núcleo |
|---|---:|---:|
| Groove | 13,28% | 12,30% |
| Groove com clique | 14,06% | 13,67% |

A diferença pequena é compatível com ruído de medição; não demonstra ganho universal. Não foi observado aumento relevante nesse ensaio. O FFT já existente é reutilizado, os buffers continuam limitados e a apresentação não grava rastreio. [JSON completo](resultado-dsp-cost-v0.29.json).

## Interface e relatório

A integração nativa usa CaptureRuntime com fonte sintética e o Stage Preview. Percorre as oito posições reais de drop, confirma o apoio por clique, mantém a saída física desativada e encerra normalmente. O relatório HTML exportado foi carregado no Qt WebEngine: metadados do WAV, quatro linhas SVG, métricas e posicionamento do áudio por clique foram verificados, sem autoplay. O navegador conectado à sessão estava indisponível; a conferência usou a integração local do próprio produto.

[JSON nativo](resultado-replay-ui-v0.29.0.json) · [Log](resultado-replay-ui-v0.29.txt) · [Prévia do relatório](../preview-replay-v0.29.png) · [Primeiro kick no palco](../preview-drop-click-v0.29.png).

O teste gráfico por software pode registrar avisos de GPU do Chromium no encerramento. Isso não altera as métricas de DSP; o funcionamento gráfico é verificado pelas capturas e pela interação do relatório. A apresentação real continua usando suas opções gráficas normais.

## Distribuição e uso real

A instalação editável, wheel 0.29.0, fontes/recursos byte a byte, compilação e ajuda dos dois comandos são verificadas em [resultado-package-v0.29.json](resultado-package-v0.29.json). O firmware 0.22 permanece idêntico; não precisa ser regravado.

[Como preparar WAV e rótulos e executar o replay](replay-causal.md). É necessário um conjunto real rotulado para calibrar e afirmar precisão no repertório do usuário. Não houve teste de seis horas reais. [Registro 0.28](validacao-v0.28.md) · [Confiabilidade](confiabilidade.md).
