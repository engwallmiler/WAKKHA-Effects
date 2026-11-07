# Validação — versão 0.41.0

Registro: **2026-11-06 UTC**. Investigação de desarmes, tolerância a atrasos breves, registro detalhado da saída com horário local do PC e separação visual entre fase e contagem acumulada. DSP, análise musical, efeitos RGB, formato USB e firmware preservados.

## Testes automatizados

**954 testes Python passaram**, sem skips, em **383,40 segundos**. Incluem DSP/estrutura, UI, MIDI, projetos, topologia, protocolo e firmware com periféricos simulados. Os novos casos cobrem recuperação breve, desarme persistente, apagamento manual durante recuperação, recarga com callback antigo, silêncio sem desarme, falha de ACK registrada, logger indisponível, disco lento/indisponível, limites/rotação, horário local, exportação e contadores além de 64 bits. [Log completo](resultado-pytest-v0.41.txt).

Depois dos últimos ajustes de contexto, aparência e fuso do Windows, **81 testes direcionados passaram** em **5,70 segundos**, incluindo saída USB, recuperação, logs, horários e tela cheia. Cinco casos adicionais conferem a API do Windows contra o fuso explícito do Qt, incluindo mudança de dia e regras históricas de verão mesmo com `TZ=GMT0`, além do fallback. [Log direcionado](resultado-output-tests-v0.41.txt).

**198 testes JavaScript passaram**, sem skips. Os dois novos testes verificam motivos de bloqueio do motor e 10.000 leituras de diagnóstico sem novos buffers de pixels ou alterações no RGB. [Log](resultado-pixel-js-v0.41.txt).

A comparação com a versão 0.40 manteve **140 quadros físicos RGB idênticos em 35 modos**. [Resultado](resultado-pixel-rgb-parity-v0.41.json).

## Falhas injetadas na interface real

Qt/WebEngine real, projeto de quatro saídas de 120 LEDs, serial emulada e arquivos de configuração temporários:

- **400 ms de bloqueio do renderer:** quadro antigo descartado, apagamento temporário e retomada com quadro novo sem reativação manual.
- **350 ms de bloqueio da GUI:** retomada sem desarme permanente, com o atraso registrado.
- **1.100 ms de bloqueio do renderer:** saída desarmada, sem retorno automático; reativação manual funciona quando a resposta antiga é liberada.
- **ACK retido:** conexão encerrada; log identifica comando FRAME, sequência, porta e TimeoutError.
- **Diálogo Qt de arquivos aberto:** envio de quadros continua.
- **Janela de logs aberta:** envio continua, filtros funcionam, exportação preserva causa anterior e horários locais; ao fechar a janela, seu timer para.

Não houve erro JavaScript. Todos os runtimes e o writer do registro encerraram. [Relatório](resultado-output-diagnostics-v0.41.0.json) · [Log](resultado-output-diagnostics-v0.41.txt).

O Windows estava em `E. South America Standard Time` (UTC−3), mas o processo recebeu `TZ=GMT0`. A API nativa preservou o horário do Windows apesar dessa divergência; o relatório inclui um exemplo com deslocamento `-03:00`. O horário não foi fixado nesse fuso. [Prévia da janela](../preview-output-logs-v0.41.0.png).

Essas reproduções demonstram os caminhos corrigidos; **não provam a causa do episódio original**, pois os arquivos anteriores não registravam os motivos da saída e o horário do incidente não foi identificado.

## Interface, MIDI e quatro saídas

O ensaio de interface conferiu palco visível nas quatro abas, janela mínima de 1100 × 760, controles de efeito único/referência, ausência de rolagem indevida, retorno de tela cheia por Esc/F11/botão e recarga. [Relatório](resultado-pixel-workspace-v0.41.0.json) · [Log](resultado-pixel-workspace-v0.41.txt).

O ensaio MIDI aprendeu onze funções, conferiu persistência, sincronismo de referência, retorno de LED, estruturas manuais, drop de oito tempos e operação minimizada. Não utilizou X1 física. [Relatório](resultado-pixel-midi-v0.41.0.json) · [Log](resultado-pixel-midi-v0.41.txt).

O teste de quatro saídas emuladas preservou GPIO 18/19/25/26, comprimentos 120/300/90/120, pacote de 1.890 bytes, cópias exatas, buffers reutilizados, minimização, blackout, redução do pacote ao desabilitar uma saída, persistência e recarga. [Relatório](resultado-pixel-four-outputs-v0.41.0.json) · [Log](resultado-pixel-four-outputs-v0.41.txt).

## Ensaio nativo de estabilidade

**60 segundos reais e oito horas musicais aceleradas**, captura sintética, uma fita lógica de 300 LEDs dividida em seis barras com pares espelhados e serial emulada. Foram **5.626 blocos de áudio, zero descartes**, **1.241 quadros USB** e aproximadamente **21,34 fps** ao final. O desenho teve média de **1,57 ms**, com buffers estáveis; o modo único não reteve snapshots de misturas.

O ensaio incluiu gravações de projeto deliberadamente lentas, rollover do identificador Qt, bloqueio de 1.100 ms do renderer com desarme, reativação manual e recarga da prévia preservando áudio/projeto. O registro terminou com **20 eventos e 58 amostras de saúde**, sem perda de escritas, falha de disco ou crescimento além dos limites. Todos os workers encerraram. [Relatório](resultado-pixel-endurance-v0.41.0.json) · [Log](resultado-pixel-endurance-v0.41.txt).

Esse avanço musical acelerado verifica contadores e estados; não equivale a oito horas reais de funcionamento. A correção final de conversão de fuso foi validada depois pelos testes direcionados e pelo ensaio específico de falhas.

## Distribuição e limites

Instalação editável e wheel são **0.41.0**. A verificação compara fontes e recursos, confere os **25 arquivos DSP/música/contratos** byte a byte contra 0.40 e valida hashes do firmware e suas fontes. [Verificação do pacote](resultado-package-v0.41.json).

Firmware permanece **0.37.0**, para GPIOs 18, 19, 25 e 26. A atualização não exige gravar o ESP32 novamente. [Registro de firmware](resultado-esp32-v0.37.json) · [Entrega anterior](validacao-v0.40.md).

Não foi realizado ensaio de seis horas reais com Traktor, X1 e fitas conectadas. Os prazos e falhas foram exercitados com dispositivos emulados. Registros do computador não determinam com certeza falhas elétricas, alimentação ou resets do ESP32. [Investigação, operação e limites](logs-saida-v0.41.md).
