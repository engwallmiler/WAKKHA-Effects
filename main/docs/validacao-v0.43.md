# Validação — versão 0.43.0

Registro: **2026-11-06 UTC**. Investigação do arquivo falha1.json, correção da idade dos quadros de pixels e instrumentação de fila/cálculo/entrega. DSP, identificação de kicks, estrutura, BPM, padrões RGB, projeto, perfis MIDI, protocolo serial e firmware preservados.

## Testes automatizados

**980 testes Python passaram**, sem skips, em **359,06 segundos**. Incluem a suíte geral e os novos testes de carimbo, atraso de fila, entrega antiga, calibração, relógio Windows de resolução grossa e não reativação após desarme. [Log completo](resultado-pytest-v0.43.txt).

Após o refinamento final de validade curta da calibração e margem de deriva, **84 testes direcionados passaram** em **1,75 segundo**. Incluem os testes de USB/painel e mais um caso avançando 48 horas de relógios com deriva. A propriedade de idade conservadora também foi verificada em 20.000 pares de horários quantizados, sem histórico crescente. [Log direcionado](resultado-frame-tests-v0.43.txt).

**212 testes JavaScript passaram**, sem skips, em **6,87 segundos**. Os novos casos conferem carimbos no instante de amostragem, independência do desenho, identidade de cópias, dados RGB e buffers preservados. [Log](resultado-pixel-js-v0.43.txt).

**140 quadros em 35 modos mantiveram RGB físico idêntico** frente à 0.42. A informação temporal adicional fica no envelope do renderizador, sem entrar nos bytes enviados às fitas. [Comparação](resultado-pixel-rgb-parity-v0.43.json).

## Incidente e reprodução com janela visível

O arquivo original registra um desarme por **781 ms sem quadro aceito**, com última resposta de **594 ms**, USB conectada e captura sem descartes. Não contém o instante real de geração do RGB. Logo, permite identificar o motivo imediato, mas não separar retrospectivamente fila, cálculo e entrega. [Resumo com hash](analise-falha1-v0.43.json) · [Investigação](correcao-falha1-v0.43.md).

O ensaio final usa Qt/WebEngine real, janela visível, modo leve desligado, Auto Show em camadas, build-up a 127 BPM, captura sintética real e quatro saídas emuladas de 120 pixels, com a quarta copiando a primeira:

- Bloqueios de 400/594/594 ms antes da geração: RGB novo aceito, retomada sem rearmar, nenhum frame_timeout nesses casos.
- Nas duas esperas de 594 ms, ida/volta observada de 546/578 ms, cálculo de 0,1 ms e idade conservadora de aproximadamente 24/32 ms.
- Retenção de 594 ms depois da geração: RGB antigo descartado; somente um quadro novo permite retomar.
- Bloqueio persistente de 1.100 ms: desarme preservado, sem retomada automática.
- Apagamento manual durante espera: callback fresco posterior não reativa a saída.
- Zero descartes de áudio, nenhum erro JavaScript e encerramento de todos os workers.

[Relatório específico](resultado-frame-freshness-v0.43.0.json) · [Log](resultado-frame-freshness-v0.43.txt).

O ensaio geral de diagnóstico também preservou apagamento em falha de ACK, comando registrado, logs não modais, exportação, horário local e quadros durante diálogos Qt. [Relatório](resultado-output-diagnostics-v0.43.0.json) · [Log](resultado-output-diagnostics-v0.43.txt).

## MIDI e compatibilidade

O ensaio adicional de **60 segundos reais / oito horas musicais aceleradas** passou com **5.629 blocos de áudio, zero descartes, 1.243 quadros USB e 21,32 fps** ao final. Buffers permaneceram estáveis, com 20 eventos, 58 amostras de saúde e zero escritas perdidas. Incluiu o desarme por bloqueio persistente, reativação, rollover Qt e recarga preservando áudio/projeto. Acelerar a música não equivale a oito horas reais. [Relatório](resultado-pixel-endurance-v0.43.0.json) · [Log](resultado-pixel-endurance-v0.43.txt).

O ensaio nativo de onze funções MIDI passou com quatro saídas emuladas, marcação/desmarcação da referência e LED, operação minimizada, drop automático de oito tempos com contador acústico em 1, silêncio e fechamento. [Relatório](resultado-pixel-midi-v0.43.0.json) · [Log](resultado-pixel-midi-v0.43.txt).

Instalação editável e wheel são **0.43.0**. A verificação confere fontes e recursos, os **25 arquivos DSP/música/contratos** byte a byte contra 0.42 e os hashes do firmware/fontes. O firmware continua **0.37.0**, GPIOs 18/19/25/26; não exige regravação. [Verificação do pacote](resultado-package-v0.43.json) · [Entrega anterior](validacao-v0.42.md).

A correção não promete emissão contínua durante uma parada real do motor. Os limites de quadros antigos, apagamento por falta de dados e falha persistente permanecem. Não foi feito ensaio de seis horas reais com ESP32/X1/fitas físicos. A origem exata da espera no incidente original continua indeterminada; os novos campos permitem investigá-la se houver recorrência.
