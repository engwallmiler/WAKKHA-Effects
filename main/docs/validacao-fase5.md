# Validação — fase 5, versão 0.4

Registro: **2026-10-12 (UTC)**. Windows x64, Python 3.12.10, NumPy 2.5.4, SciPy 1.18.1, PySide6 6.12.0 e PyAudioWPatch 0.2.12.9. Não foram acrescentadas dependências nesta fase.

## Testes automatizados

**147 testes passaram em 21,91 s**, incluindo os 112 casos anteriores. Evidência: resultado-pytest.txt. O registro da fase 4 foi preservado em validacao-fase4.md e resultado-pytest-fase4.txt.

| Área | Verificação desta fase |
|---|---|
| Tempo constante | Aquisição e sincronismo em 90/120/128/138/160 BPM; erro final de BPM inferior a 0,2 e próxima batida dentro de 20 ms nos eventos sintéticos regulares. |
| Instabilidade | Jitter determinístico de até 8 ms e contratempos extras mantêm o BPM principal; eventos irregulares do teste não terminam sincronizados. |
| Mudança gradual | Rampa de 120 a 135 BPM em 90 intervalos; erro final inferior a 1,2 BPM, sem reiniciar a contagem relativa. |
| Mudança maior | Sequência em 120 BPM seguida de 145 BPM provoca nova aquisição e termina sincronizada no novo andamento. |
| Ausência de kicks | Manutenção estimada, redução de confiança, recuperação de fase e expiração após o prazo. |
| Sem callbacks | Projeção pura e GUI expiram o relógio mesmo sem blocos novos; não exibem previsão indefinidamente. |
| Aquisição incompleta | Poucos eventos sem referência posterior expiram; eventos históricos não são reingeridos. |
| Metade/dobro | Faixa ampla prefere o tempo observado; kicks esparsos e de densidade dupla expõem ambiguidades e hipóteses fora da faixa preferida. |
| Estado | Deduplicação de kicks refinados, limites fracionários de BPM, reset de relógio e históricos limitados. |
| Pipeline de áudio | Sinal sintético a 128 BPM atravessa o detector de kicks e termina com tracker sincronizado, dentro de 0,6 BPM. |
| Falhas | Falha opcional do tracker mantém kicks, espectro e medidores e não gera repetição excessiva de logs; lacuna de captura elimina referência antiga. |
| Preferências | Migração v3 → v4 preserva os ajustes de kick do usuário; validação, importação aplicada e rejeição de parâmetros inválidos. |
| Interface | Rhythm Monitor inicia/para, mostra dados reais do pipeline, congela após parar, bloqueia ajustes durante captura e limpa hipóteses antigas após perda da referência. |

Esses testes não são uma avaliação de acurácia em um conjunto de músicas reais.

## Sessão sintética com entrega em tempo real

Em 12 s, com 48 kHz, estéreo e blocos de 512:

- 1.125 blocos recebidos, zero descartes e zero falhas de continuidade.
- 23 kicks; tracker sincronizado em aproximadamente 120,000 BPM, confiança heurística final de 96% e 19 kicks alinhados após aquisição.
- Sem erros de captura, espectro, kicks ou tracker.
- Em 935 snapshots observados, processamento médio de 3,77 ms, percentil 95 de 6,62 ms e máximo de 11,10 ms.
- Históricos limitados: 16 eventos de kick, 200 pontos de atividade e 47 pontos de andamento nesse intervalo.

Evidência: resultado-sintetico-fase5.json. A renderização Qt foi executada em paralelo a essa verificação. A amostragem por polling não observa necessariamente todos os blocos. Os números não medem CPU total, latência acústica ou estabilidade em sessões prolongadas.

## Interface

As cinco páginas de captura, espectro, kicks, ritmo e configurações foram renderizadas em 1440 × 960 com a fonte sintética. O Rhythm Monitor foi inspecionado visualmente: BPM, fase, estado, hipóteses e histórico receberam dados do pipeline ativo. Evidência visual: preview-ritmo.png. Páginas longas usam rolagem.

## Avaliação do usuário e Traktor

O usuário aprovou a captura/DSP com Traktor usando a saída do notebook e, em seguida, relatou que os kicks da fase 4 foram detectados quase perfeitamente, com resultado muito satisfatório. Esse é um relato funcional do cenário do usuário, sem métricas inventadas dessa sessão.

**O BPM/PLL da fase 5 ainda precisa ser comparado com faixas reais no Traktor.** Os testes desta entrega não alteraram a saída do Windows, não reproduziram som e não gravaram áudio bruto.

## Roteiro para a fase 5

1. Reiniciar iniciar.cmd, capturar a saída usada pelo Traktor e abrir Rhythm Monitor.
2. Comparar o BPM estimado com o Traktor em trechos regulares de house/techno. Aguardar vários kicks até sincronizar.
3. Observar o pulso de fase, a próxima batida e o erro de ajuste. A contagem é relativa e não indica compasso.
4. Alterar lentamente o pitch no Traktor e acompanhar a mudança de BPM.
5. Usar uma pausa curta de kicks, depois uma pausa acima do limite de manutenção: verificar estimado, redução de confiança e perda de referência.
6. Avaliar faixas que possam provocar metade/dobro. Ajustar a faixa preferida com captura parada, salvar e reiniciar.
7. Acompanhar descartes, continuidade e tempo DSP em uma sessão prolongada. Exportar diagnóstico se necessário.

Depois da avaliação deste tracker, a fase 6 será o motor abstrato de iluminação; simulador, estrutura musical e saídas físicas seguem suas fases próprias.
