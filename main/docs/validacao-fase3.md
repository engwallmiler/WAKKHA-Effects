# Validação — fase 3, versão 0.2

Registro: **2026-10-12 (UTC)**. Ambiente: Windows x64, Python 3.12.10, NumPy 2.5.4, SciPy 1.18.1, PySide6 6.12.0, PyAudioWPatch 0.2.12.9.

## Testes automatizados

**81 testes passaram em 3,85 s**, incluindo os 36 casos da fundação/captura. Evidência: **resultado-pytest.txt**. As versões completas estão em **requirements-windows-py312.lock.txt**.

| Área acrescentada | Evidência |
|---|---|
| Calibração espectral | Senoides conhecidas em 44,1 e 48 kHz, RMS absoluto, frequência dominante e banda esperada. |
| Energia unilateral | Tratamento correto de DC/Nyquist e silêncio finito. |
| Estéreo | Sinal em oposição de fase mantém energia no espectro. |
| Acumulação | Blocos de 113 amostras e sinal contínuo produzem os mesmos quadros e timestamps. |
| FFT configurável | Janelas de 1024 a 8192 e diferentes sobreposições alteram corretamente a duração e o passo. |
| Filtros | Seletividade passa-baixa, passa-alta e passa-banda; equivalência de processamento em blocos; reset e canais independentes. |
| Pré-processamento | Remoção de DC, preservação das amostras capturadas e normalização com limite de ganho/pico. |
| Transientes | Grave constante sem disparos repetidos; ataques sintéticos, intervalo refratário, confiança limitada e robustez a ganho menor. |
| Descontinuidade | Amostras de lados diferentes de uma perda não são juntadas em uma janela FFT. |
| Falha DSP | Pré-filtro inválido para Nyquist mantém medidores, informa erro e evita repetição excessiva de logs; outro formato permite recuperação. |
| Preferências | Migração v1 → v2 preserva captura e dispositivo; DSP inválido é rejeitado. |
| GUI | Iniciar/parar pelo painel espectral, estados visuais, bloqueio de parâmetros durante captura, importação efetivamente aplicada e preservação dos ajustes após erro. |

## Inspeção visual

As três páginas foram renderizadas em **1440 × 960** usando a fonte sintética. Prévia do monitor: preview.png. Espectro: preview-espectro.png. Configurações: preview-configuracoes.png.

Os dados são de teste e a origem aparece explicitamente na interface. As páginas espectral e de configurações usam rolagem quando a altura disponível não acomoda todos os controles.

## Verificação com WASAPI real

Uma tentativa de aproximadamente **10,45 s** na saída **Auscultadores (2- Realtek(R) Audio)** abriu e encerrou corretamente em **48 kHz, estéreo, float32, blocos de 512**, sem erro de captura ou análise. A saída não entregou blocos nessa tentativa.

O resultado é **inconclusivo para análise de sinal real**; não foram produzidos espectros nem métricas DSP de áudio real nessa execução. A evidência está em **resultado-loopback-fase3.jsonl**, com validation=inconclusive_no_playback.

A verificação anterior da versão 0.1 recebeu 2.816 blocos silenciosos em 30 segundos sem perdas. Esse resultado histórico está em **validacao-fase1-2.md** e **resultado-loopback.jsonl** e não é apresentado como validação do novo DSP com música.

Não foi gerada reprodução sonora nem alterada a saída padrão do Windows para fabricar uma condição de teste. Não foi salvo áudio bruto.

## Roteiro com música real

1. Reiniciar BEATLIGHT e selecionar a saída utilizada pelo Traktor em WASAPI compartilhado.
2. Reproduzir uma faixa e confirmar que forma de onda, RMS e espectro acompanham o áudio.
3. Observar graves, médios e agudos em faixas de house/techno com diferentes masterizações.
4. Parar a captura, alterar FFT/sobreposição, salvar e reiniciar; conferir resolução e janela indicadas.
5. Comparar o pré-filtro desativado e passa-banda 40–150 Hz: o espectro muda enquanto os medidores de entrada continuam mostrando o sinal original.
6. Pausar e retomar o áudio; confirmar ausência de erro por saída inativa. Repetir iniciar/parar e troca de dispositivo.
7. Manter uma sessão prolongada com o Traktor e acompanhar descartes, continuidade, atualização da GUI e tempo de processamento.

Não existe garantia de latência inferior a 100 ms. Contagens de transientes não representam BPM nem kicks identificados. A identificação de instrumentos requer a próxima fase e validação própria.
