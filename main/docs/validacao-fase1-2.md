# Validação do protótipo

Registro da entrega: **2026-10-12 (UTC)**. Não constitui homologação com música real ou hardware DMX.

## Ambiente verificado

- Windows x64 do computador do usuário.
- Python portátil oficial **3.12.10**, isolado no projeto.
- NumPy **2.5.4**, PySide6 **6.12.0**, PyAudioWPatch **0.2.12.9**, Pytest **9.1.1**.
- A lista completa está em **requirements-windows-py312.lock.txt**.

## Testes automatizados

**36 testes passaram em 0,93 s** na execução final. Evidência: **resultado-pytest-fase1-2.txt**.

| Área | Casos verificados |
|---|---|
| Medidores | RMS/pico de senoide conhecida, estéreo com amplitudes distintas, silêncio finito, clipping, transiente de uma amostra, amostras inválidas e continuidade. |
| Fluxo | Descarte do bloco antigo, contagem de perdas, fila vazia, reset e sobrecarga induzida com consumidor lento. |
| Configuração | JSON atômico, recuperação de arquivo inválido, tipos/limites, versões e importação. |
| WASAPI com adaptador falso | Descoberta, saída padrão, mudança de índice, float32 somente leitura, timestamps, overflow, erro de callback, falha de abertura/recuperação e stream inativo. |
| Dispositivos | Remoção durante captura e mudança do padrão, preservando a saída escolhida; verificados com dispositivos simulados. |
| Formatos | Taxas nativas de 44,1 e 48 kHz, sem conversão; verificação de contrato com adaptador falso. |
| Runtime | Cinco ciclos iniciar/parar, silêncio, falha inicial, desconexão assíncrona, recuperação e ausência de threads de captura residuais. |
| Interface Qt | Comandos reais iniciar/parar, bloqueio dos seletores durante captura, snapshots gráficos, navegação, importação e fechamento assíncrono. |
| Diagnóstico | Registro JSON com timestamp UTC e contexto Unicode. |

A interface também foi renderizada em **1440 × 960**, com sinal sintético e renderização Qt, e inspecionada visualmente. O arquivo **preview.png** representa o aplicativo real; os dados nele são de teste, identificados na interface.

## Verificação com dispositivos reais

A descoberta encontrou:

- **Auscultadores (2- Realtek(R) Audio)** — 48 kHz, 2 canais.
- **Altofalantes (2- Realtek(R) Audio)** — 48 kHz, 2 canais, padrão do Windows no momento da verificação.
- **Q27G2SG4 (NVIDIA High Definition Audio)** — 48 kHz, 2 canais.

Na saída Realtek de fones, a execução contínua final teve:

| Métrica | Resultado |
|---|---|
| Tempo incluindo abertura/fechamento | 30,11 s |
| Blocos recebidos | 2.816 |
| Formato | 48 kHz, 2 canais, float32, 512 frames |
| Blocos descartados | 0 |
| Falhas de continuidade observadas | 0 |
| Erros de captura | 0 |
| Latência informada pelo driver | 22 ms |
| Processamento do último bloco | Aproximadamente 1,43 ms |
| Sinal presente | **Silêncio**: RMS/pico −120 dBFS |

A evidência JSON, sem amostras de áudio, está em **resultado-loopback.jsonl**. O tempo do último bloco não é média nem percentil de desempenho.

Também foram realizados três ciclos reais de aproximadamente dois segundos em cada uma das duas saídas Realtek e um teste de seis segundos por saída. A saída de fones entregou blocos silenciosos sem perdas; a saída de alto-falantes abriu e fechou corretamente, mas não entregou blocos enquanto estava sem reprodução. Esse resultado é **inconclusivo para captura de sinal**, e a aplicação mantém a captura aberta nessa condição.

Não foi reproduzido áudio pelo teste, nem alterada a saída padrão do Windows. A inspeção foi somente da mixagem de saída, sem uso de microfone e sem salvar áudio.

## Aceitação ainda necessária com o Traktor

1. Reproduzir uma faixa no Traktor Pro 3, usando mixer interno e a saída Realtek em WASAPI compartilhado.
2. Selecionar a mesma saída no BEATLIGHT e confirmar níveis e forma de onda correlacionados com a reprodução.
3. Manter a sessão por pelo menos 30 minutos, acompanhando descartes, continuidade e responsividade.
4. Repetir iniciar/parar e alternar entre saídas disponíveis, sempre parando antes da troca.
5. Testar pausa prolongada, retorno da reprodução e mudança do dispositivo padrão; o dispositivo escolhido deve ser mantido e a mudança deve gerar aviso.
6. Desconectar fisicamente ou desativar a saída selecionada, confirmar erro controlado e recuperação após atualização/reinício.
7. Validar 44,1 kHz em um endpoint que realmente ofereça esse formato, além dos 48 kHz verificados aqui.
8. Avaliar a idade estimada dos blocos e a resposta visual sob carga simultânea do Traktor. A meta de menos de 100 ms permanece uma meta experimental.

**Conclusão de escopo:** fundação e protótipo de captura implementados e testados. A aceitação operacional com áudio real do Traktor ainda depende dos passos acima. Os resultados de sinais sintéticos e de silêncio não substituem essa validação.
