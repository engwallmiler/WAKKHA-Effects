# Validação — versão 0.27.0

Registro: **2026-10-29 (UTC)**. Detector complementar de ataques mascarados por bassline, aquisição da grade entre candidatos intermediários, ajuste inicial de período e saneamento do perfil/cauda sob fundo grave. Sem captura física, COM ou Link nativo nos ensaios desta entrega.

## Regressão

**759 testes Python** cobrem DSP, clocks, estrutura, drops, projetos, interface e transporte. Incluem sinais com baixo sustentado/contratempo/compressão, 100/120/128/150 BPM, fase estéreo oposta, diferentes ganhos/tamanhos de bloco, vibrato, reinício do sensor, cauda abaixo do fundo e aquisição com candidatos intermediários. A regressão de intervalo mínimo usa tolerância numérica de 1 ns para representar 400 ms em ponto flutuante; bloqueios em escala de amostras/quadros continuam exigidos. [Saída completa](resultado-pytest-v0.27.txt).

**78 testes JavaScript** verificam o motor de pixels e sua integração. Não houve alteração dos efeitos ou do protocolo físico nesta rodada. [Saída completa](resultado-pixel-js-v0.27.txt).

## Matriz comparativa e limites

[validate_kick_masking.py](../scripts/validate_kick_masking.py) compara o código atual com o wheel 0.26.0 preservado, sem substituir a instalação. Oito arranjos determinísticos têm tempos de kick conhecidos e picos abaixo de 1,0. Cada associação evento/verdade é única e exige proximidade de até 75 ms. Candidatos brutos e confirmações da estrutura são contados separadamente.

A 0.27 preservou os kicks isolados, confirmou todos os kicks nos casos de baixo sustentado, contratempo e compressão, e nos contratempos de 100/128/150 BPM. A linha rápida permaneceu com 9/12 acertos, reduzindo falsas confirmações de 3 para 1. Não se afirma acurácia equivalente em faixas reais ou separação completa de kick/baixo.

No retorno com baixo forte, a 0.26 não entrou no drop no trecho até 13 s; a 0.27 decidiu no primeiro kick em 12,064 s, usando a verdade de 12 s. Isso não mede latência completa de captura, apresentação e fita física. Casos anteriores de roll fraco, baixo sem kick, pausa e primeiro impacto continuam na regressão ampla.

[Referência 0.26](resultado-kick-masking-v0.26.0.json) · [Resultado 0.27](resultado-kick-masking-v0.27.0.json) · [Log](resultado-kick-masking-v0.27.txt) · [Tabela e explicação](kicks-baixo.md).

O processamento comparativo de 56 s de áudio consumiu aproximadamente 5,00 s → 5,33 s de CPU: 8,93% → 9,51% de um núcleo, sem GUI. A medição é local, curta e sequencial; a diferença não deve ser projetada como uma garantia de consumo no computador inteiro. O sensor reutiliza o FFT existente, sem modelo ou dependência adicional, com buffers limitados.

## Interface nativa

[validate_kick_masking_ui.py](../scripts/validate_kick_masking_ui.py) passou com fonte sintética de baixo sustentado e canais em oposição de fase. Em oito segundos: **749 blocos, zero descartados, 15 candidatos, 15 confirmações e 15 eventos pelo sensor espectral**. Verificou tabela com coluna Sensor, limite de 200 pontos e encerramento limpo. A saída física permaneceu desativada.

[JSON nativo](resultado-kick-masking-ui-v0.27.0.json) · [Log nativo](resultado-kick-masking-ui-v0.27.txt) · [Captura inspecionada](../preview-kicks-baixo-v0.27.png).

As curvas agora separam energia/limiar e novidade/limiar; marcações verdes indicam confirmação e azuis discretas indicam candidatos. Força relativa deixou de ser apresentada como potência isolada de um kick. O gráfico continua sendo atualizado somente quando visível e com desenhos habilitados.

## Distribuição

Instalação editável e wheel **0.27.0**, compilação de src/scripts, `iniciar.cmd --help`, exemplos validados e identidade dos arquivos são conferidos em [resultado-package-v0.27.json](resultado-package-v0.27.json). O firmware 0.22 permanece idêntico e compatível, sem regravação. Preferências existentes são preservadas.

Não houve ensaio de seis horas reais nem calibração com tracks fornecidas pelo usuário. O funcionamento minimizado/modo leve da 0.26 permanece; a nova análise continua necessária em segundo plano. [Histórico 0.26](validacao-v0.26.md) · [Confiabilidade](confiabilidade.md) · [Guia dos kicks](kicks-baixo.md).
