# DSP — fase 3, versão 0.2

## Fluxo implementado

~~~mermaid
flowchart LR
    A[AudioBlock original] --> B[LevelAnalyzer]
    A --> C[Pré-processamento causal]
    C --> D[FFT incremental por canal]
    D --> E[Potência média dos canais]
    E --> F[Faixas logarítmicas e energia por bandas]
    E --> G[Fluxo espectral e transientes genéricos]
    B --> H[MonitorSnapshot]
    F --> H
    G --> H
    H --> I[Interface Qt e diagnóstico]
~~~

O bloco capturado permanece float32 e somente leitura. Filtros utilizam float64 internamente para estabilidade numérica. O medidor de entrada e a forma de onda usam o sinal original; a cadeia de pré-processamento afeta a análise espectral e os transientes.

## Componentes

| Arquivo | Responsabilidade |
|---|---|
| dsp/config.py | DspConfig imutável: FFT, sobreposição, DC, pré-filtro e divisões de bandas. |
| dsp/filters.py | StreamingFilter Butterworth SOS causal, estado por canal e FilterBank para várias bandas. |
| dsp/preprocess.py | Remoção opcional de DC, pré-filtro e operações explícitas de mono/normalização. |
| dsp/spectrum.py | StreamingSpectrum: acumulação limitada, Hann, FFT, potência e redução para 96 colunas. |
| dsp/transients.py | TransientDetector genérico com histórico, limiar adaptativo, confiança heurística e período refratário. |
| dsp/pipeline.py | AudioAnalyzer: compõe os módulos, preserva os medidores e publica snapshots. |
| ui/spectral.py | Apresenta o espectro, bandas, transientes e controles de captura. Não calcula FFT ou descritores. |
| ui/dsp_settings.py | Formulário DSP e transferência de valores para Settings. |

## FFT e níveis

- FFT real por canal, com janelamento Hann e tamanhos **1024, 2048, 4096 e 8192**.
- Sobreposição configurável em **25, 50 ou 75%**. O passo é FFT × (1 − sobreposição).
- Padrão: **2048 amostras / 75%**, ou janela de **42,67 ms** e passo de **10,67 ms** em 48 kHz.
- Resolução nominal em frequência: taxa de amostragem / tamanho da FFT; **23,44 Hz** no padrão em 48 kHz.
- A potência é calculada por canal e depois promediada. Isso evita perder um sinal estéreo em oposição de fase ao somar as amostras antes da FFT.
- A normalização de potência utiliza a energia da janela. DC e Nyquist não recebem o fator de duplicação dos demais bins do espectro unilateral.
- Os níveis exibidos são **RMS em dBFS**, com piso de −120 dBFS. Uma senoide de amplitude de pico 0,5 tem aproximadamente **−9,03 dBFS RMS**.
- As 96 colunas logarítmicas somam a potência dos bins em cada faixa. Colunas abaixo da resolução da FFT podem não conter um bin; não são preenchidas com valores inventados.
- A frequência dominante é a posição do bin de maior potência na região visível. Sua precisão é limitada pela resolução indicada; não há reconhecimento de nota ou instrumento.

Bandas padrão: **20–250 Hz**, **250–2000 Hz**, **2000–20000 Hz**. As duas divisões internas são configuráveis. Cada banda informa RMS e participação na soma de energia dessas três bandas. As porcentagens excluem DC e frequências fora de 20 Hz–20 kHz; em silêncio são zero. O espectro é limitado pelo Nyquist da fonte.

A acumulação preserva as janelas entre blocos e produz todos os quadros completos. Ao final de cada chamada, permanece menos de uma janela pendente. Mudar a taxa, os canais, a fonte ou detectar descontinuidade reinicializa filtros e acumulação, evitando juntar amostras de lados diferentes de uma perda.

## Filtros e pré-processamento

Remoção de DC padrão: passa-alta Butterworth de segunda ordem em **20 Hz**. O pré-filtro adicional é opcional, de quarta ordem, com modos passa-baixa, passa-alta e passa-banda. Os cortes são validados contra a frequência de Nyquist quando a fonte efetiva é conhecida.

São filtros causais, com estado persistente entre blocos. Não se usa filtfilt nem análise de áudio futuro. O atraso de fase depende da frequência; os timestamps da janela não constituem uma compensação desse atraso.

O FilterBank permite saídas de bandas simultâneas e compartilha a conversão de entrada. O pipeline atual usa StreamingFilter para DC e pré-filtro; o banco está disponível e testado como componente para os próximos detectores.

stereo_to_mono oferece média explícita dos canais para consumidores que precisarem de sinal mono. A FFT usa potência por canal para preservar sinais em oposição de fase. normalize_for_analysis implementa ganho limitado e teto de pico; essa normalização não é ativada automaticamente, preservando a dinâmica da música.

## Transientes

O detector combina fluxo espectral positivo e aumento de energia. O limiar utiliza mediana e desvio absoluto mediano do histórico recente, com piso mínimo. Existe aquecimento de oito comparações, gate de nível e período refratário padrão de **90 ms**.

Cada evento fornece instante estimado, instante de detecção, intensidade e confiança. O instante estimado é o centro da janela; não é um onset refinado amostra a amostra. A confiança é um indicador heurístico e não uma probabilidade calibrada.

O contador pertence à sessão. Uma descontinuidade reinicia o histórico adaptativo, preservando a contagem de eventos já observados. A GUI consulta o contador e o último evento; não depende de receber cada evento em sua frequência de renderização.

**Transiente não significa kick.** Hi-hats, snares, entradas de sintetizadores e outras mudanças abruptas podem disparar o detector. BPM, instrumentos e estrutura musical são responsabilidades das próximas fases. Detectores futuros poderão operar em caminhos de análise próprios, sem depender do pré-filtro escolhido para inspeção visual.

## Falhas e compatibilidade

Uma falha opcional de processamento espectral é registrada uma vez para o formato afetado e aparece na interface. A medição original e a captura continuam. Uma nova sessão ou mudança de formato permite reavaliar a análise. Blocos de áudio estruturalmente inválidos continuam sendo falhas de integridade da captura.

Settings usa **formato v2**. Preferências v1 recebem parâmetros DSP padrão, preservando dispositivo, tamanho de bloco, fila, silêncio e taxa de atualização. Carregar não sobrescreve o arquivo antigo; salvar/exportar produz v2. Versões desconhecidas e parâmetros inválidos seguem o fallback existente.

## Validação

Os testes utilizam sinais conhecidos para conferir calibração RMS, DC/Nyquist, frequências por banda, estéreo em oposição de fase, equivalência entre blocos pequenos e sinal contínuo, seletividade dos filtros, continuidade dos estados, preservação do áudio original, transientes, silêncio, falhas e migração.

As capturas de tela da interface utilizam exclusivamente a fonte sintética, agora com componentes graves, médios e agudos. Não representam análise de uma faixa real do Traktor.

## Referências

- [numpy.fft.rfft](https://numpy.org/doc/stable/reference/generated/numpy.fft.rfft.html): FFT real e espectro unilateral.
- [numpy.hanning](https://numpy.org/doc/stable/reference/generated/numpy.hanning.html): janela Hann.
- [scipy.signal.butter](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.butter.html): projeto Butterworth em seções de segunda ordem.
- [scipy.signal.sosfilt](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.sosfilt.html): filtragem causal com estado entre blocos.
