# Validação — versão 0.28.0

Registro: **2026-10-30**. Correção da prioridade dos candidatos na grade estimada pelo áudio, BPM inteiro estável como padrão e modo fixo opcional. Não houve captura de tracks reais, abertura de COM ou uso de Link nativo nestes ensaios.

## Regressão

**789 testes Python passaram**, incluindo DSP, relógios, estrutura, drops, interface, projetos e transporte. A rodada acrescenta jitter sem oscilação do inteiro, mudança persistente de andamento, correção de fase, proteção de meio tempo, ataque antecipado sem bloquear o kick seguinte, 44,1/48 kHz, ganho baixo, blocos de 113/512 amostras, silêncio/baixo sustentado/vibrato com grade ativa, reinício após perda e persistência dos modos de BPM. Proteções contra baixo sem kick e roll fraco acelerado são verificadas também no modo inteiro. [Log completo](resultado-pytest-v0.28.txt).

**78 testes JavaScript passaram** no motor de pixels. Os efeitos, o transporte USB e o firmware não foram alterados. [Log](resultado-pixel-js-v0.28.txt).

## Comparação com a 0.27

[validate_audio_grid.py](../scripts/validate_audio_grid.py) processa três sinais de 14 s, com kicks conhecidos e um ataque de baixo 110 ms antes de cada kick a partir do trecho intermediário. A grade é estimada somente pelo áudio. As versões usam suas preferências padrão: contínuo na 0.27 e inteiro na 0.28. Portanto, o ensaio compara o comportamento entregue ao operador, não isola cada alteração do algoritmo. A referência é importada do wheel preservado, sem reinstalação.

Uma confirmação deve corresponder a um único kick conhecido a até 75 ms; as demais são falsas confirmações nesse sinal.

| BPM | Kicks conhecidos | Corretos 0.27 | Falsos 0.27 | Corretos 0.28 | Falsos 0.28 |
|---|---:|---:|---:|---:|---:|
| 100 | 22 | 8 | 3 | 22 | 0 |
| 128 | 28 | 20 | 0 | 28 | 0 |
| 150 | 33 | 11 | 0 | 33 | 0 |

Na 0.28, o período ficou exatamente em 60/100, 60/128 e 60/150 após a estabilização. Os candidatos brutos de baixo continuam visíveis no diagnóstico e não se confundem com a contagem de kicks confirmados. O caso de um hop enviesar 150 BPM para 149 também tem regressão própria.

[Referência 0.27](resultado-grade-audio-v0.27.0.json) · [Resultado 0.28](resultado-grade-audio-v0.28.0.json) · [Log](resultado-grade-audio-v0.28.txt) · [Critérios e uso](grade-audio-estavel.md).

O código atual consumiu 4,25 s de CPU para os 42 s de áudio desse ensaio sem GUI, cerca de 10,1% de um núcleo. É uma medição local curta, sem execução simultânea do pytest; não estima o consumo total com Traktor nem certifica operação prolongada. Os estados continuam limitados, sem modelo externo ou nova dependência.

## Interface nativa

[validate_audio_grid_ui.py](../scripts/validate_audio_grid_ui.py) usa o arranjo de baixo antecipado a 128 BPM em estéreo com canais em oposição de fase. Em aproximadamente oito segundos, confirmou 16 kicks, manteve o período 0,46875 s e registrou zero descartes de áudio. Verificou o modo inteiro, o atalho até a seção de BPM, a tabela de seis colunas e encerramento limpo; USB permaneceu desativado.

A captura foi inspecionada: linhas verdes indicam confirmação; candidatos brutos ficam como marcas curtas na base e a previsão tem guias próprias. O gráfico continua sujeito à visibilidade e ao modo leve, sem desenho em segundo plano. O formulário foi conferido com os três modos de BPM e o valor fixo inteiro.

[JSON nativo](resultado-grade-audio-ui-v0.28.0.json) · [Log](resultado-grade-audio-ui-v0.28.txt) · [Kick Monitor](../preview-grade-audio-v0.28.png).

## Distribuição e limites

Instalação editável e wheel **0.28.0**, compilação de src/scripts, `iniciar.cmd --help` e identidade dos arquivos são verificadas em [resultado-package-v0.28.json](resultado-package-v0.28.json). O firmware 0.22 permanece idêntico e compatível; não é necessário regravar o ESP32. As preferências v13 existentes recebem o modo inteiro por padrão sem perder ajustes anteriores.

O áudio da imagem do usuário não foi disponibilizado para reprodução. Os bons resultados acima valem para os sinais descritos; não comprovam acurácia equivalente no repertório real ou separação infalível de instrumentos. Não foi realizado ensaio de seis horas reais. [Registro 0.27](validacao-v0.27.md) · [Confiabilidade](confiabilidade.md).
