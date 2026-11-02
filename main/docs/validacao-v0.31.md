# Validação — versão 0.31.0

Grade virtual de picos acústicos recorrentes, sem alteração do estimador bruto de BPM, FFTs, motor visual ou firmware. Os ensaios desta rodada são sintéticos; não abriram áudio, Link nativo, COM ou LEDs físicos.

## Regressão

**831 testes Python passaram** na suíte completa, em 366,32 segundos. [Log](resultado-pytest-v0.31.txt) · [JUnit](resultado-pytest-v0.31.xml). Inclui aquisição/continuidade da grade, mascaramento, identidade, retorno de drop, oito kicks, captura, Link emulado, UI, projetos e transporte USB emulado.

**91 testes JavaScript passaram**, sem alteração do HTML/motor de efeitos em relação à versão 0.30. [Log](resultado-pixel-js-v0.31.txt). A [validação visual anterior](validacao-v0.30.md) conserva seus limites e resultados.

## Comparação causal por blocos

[validate_peak_grid.py](../scripts/validate_peak_grid.py) executa os mesmos sinais com o wheel 0.30 e com as fontes atuais. Rótulos são usados para medir, depois de processar o áudio. Tolerância de associação: 75 ms; período obtido somente por áudio.

| Cenário | 0.30 | 0.31 | Falsos / drops falsos | BPM estável |
|---|---:|---:|---:|---:|
| Kick + baixo contínuo 65 Hz | 20/24 | 22/24 | 0 / 0 | 128 |
| Kick + baixo contínuo 65 Hz mais forte | 20/24 | 22/24 | 0 / 0 | 128 |
| Kick + baixo 105 Hz, 48 kHz | 22/24 | 22/24 | 0 / 0 | 128 |
| Kick + baixo 105 Hz, 44,1 kHz / blocos 113 | 21/24 | 21/24 | 0 / 0 | 128 |
| Kicks retirados após aquisição; baixo sustentado | 9/9 | 9/9 | 0 / 0 | 128 |
| Kicks retirados; ataques de baixo no contratempo | 9/9 | 9/9 | 0 / 0 | 128 |

Nos dois últimos cenários os nove kicks pertencem ao começo da faixa. Depois de retirados, não houve novos kicks ou drops. Nos dois primeiros houve duas recuperações adicionais em cada cenário, com disponibilidade máxima de 178,25 ms e 168,75 ms após o início rotulado, incluindo FFT e blocos.

[Referência](resultado-peak-grid-reference-v0.30.json) · [Atual](resultado-peak-grid-v0.31.json). São sinais conhecidos e curtos, não uma estimativa de acerto em faixas reais. Ainda há kicks perdidos; baixos percussivos coincidentes continuam ambíguos. O [replay causal](replay-causal.md) permite avaliar músicas rotuladas.

Os testes adicionais cobrem aquisição no máximo real, previsões sem ataque, espectro/potência incompatíveis, sustentação, contratempo, troca de BPM, limites de memória e aquisição independente de uma fase anterior errada. Quatro picos coerentes corrigem a fase da grade sem recalcular o período.

## Monitor nativo

[validate_peak_grid_ui.py](../scripts/validate_peak_grid_ui.py) gera áudio sintético, processa a análise e exibe o snapshot na aplicação Qt sem iniciar captura ou saída. Verifica o sensor **Pico + BPM**, seis colunas, detalhes de espectro/forma/potência e USB desarmado.

[Resultado](resultado-peak-grid-ui-v0.31.json) · [Imagem](../preview-peak-grid-v0.31.png).

## Custo e operação prolongada

[measure_dsp_cost.py](../scripts/measure_dsp_cost.py) fez três execuções de oito segundos por cenário, sequencialmente entre versões, sem GUI, trace ou pytest simultâneo. Medianas de um núcleo:

- Groove: 16,99% na referência → 16,60% na atual.
- Groove com clique: 17,77% → 17,58%.

A diferença está dentro da variação local; não demonstra ganho de desempenho. [Referência](resultado-dsp-cost-reference-v0.30.json) · [Atual](resultado-dsp-cost-current-v0.31.json). Todos os históricos/fila novos têm limites fixos; não foi feito novo ensaio de seis horas com Traktor/hardware. [Confiabilidade](confiabilidade.md).

## Distribuição e operação

O pacote 0.31 conserva o HTML do Pixel Studio, detector bruto, estimador de BPM, extrator estrutural, critérios próprios do drop e firmware 0.22 byte a byte contra a referência. [Verificação do wheel](resultado-package-v0.31.json). Inclui o novo módulo, guia, medições e relatórios declarados no projeto. Fontes e recursos são comparados ao wheel; a versão da instalação editável também é conferida.

Reinicie a aplicação e a captura; mantenha **BPM inteiro estável** em Configurações. Não é necessário regravar o ESP32. [Operação e limites da nova grade](grade-picos-v0.31.md).
