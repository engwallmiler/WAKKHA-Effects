# Validação — versão 0.40.0

Registro: **2026-11-05**. Efeito único, repertório/duração personalizados, intervalos até 128 compassos, referência de trocas com MIDI e revisão de buffers. O detector musical, os contratos e o firmware permanecem preservados.

## Testes completos

**938 testes Python passaram**, sem skips, em **352,34 segundos**. Incluem DSP, UI, MIDI, projetos, USB, topologia e sketch com periféricos simulados. Novos casos cobrem perfis MIDI v1 → v2 sem reassociar controles, a décima primeira ação, retorno de LED, projeto com intervalos longos/regras personalizadas e rollover do identificador de entrega dentro do inteiro Qt. [Log](resultado-pytest-v0.40.txt).

**196 testes JavaScript passaram**, sem skips. O novo conjunto verifica um padrão estável, dois durante a fusão, liberação do anterior, ausência de snapshots em interrupções rápidas, fusão curta com tempo solo mesmo após retorno de estrutura, repertório/durações por efeito, controles reais do formulário, 32/64/128 compassos, referência sem alterar BPM/projeto, pacotes atrasados, longas interrupções, correções de relógio, drops de oito tempos e quatro saídas físicas coerentes. Também cobre 48 horas de tempo musical acelerado com buffers/histórias limitados. [Log](resultado-pixel-js-v0.40.txt).

O teste de sincronismo cromático confirma que a idade da paleta permanece após Sincronizar 1/8, incluindo paletas compartilhadas durante uma fusão. O modo de demonstração respeita Manter padrão.

A referência 0.39 conservou **140 quadros RGB idênticos em 35 modos** com a apresentação em camadas. O modo único altera os desenhos deliberadamente e tem seus próprios testes. [Comparação](resultado-pixel-rgb-parity-v0.40.json).

## Interface, MIDI e quatro saídas

O ensaio Qt/WebEngine confirmou prévia visível nas quatro abas e na janela mínima de 1100 × 760, incluindo modo único, referência marcada e editor com 33 efeitos. Não houve rolagem do documento principal nem erros JavaScript. Esc, F11 e botão retornaram da tela cheia, restaurando a janela maximizada; recarga também sai desse modo. [Relatório](resultado-pixel-workspace-v0.40.0.json) · [Log](resultado-pixel-workspace-v0.40.txt).

O ensaio MIDI aprendeu **onze funções**, sem executar gestos de aprendizado nem congelar o Auto Show, e salvou o perfil explicitamente. Exercitou o modo único com quatro fitas emuladas de 120 LEDs, marcou a referência por MIDI e conferiu o LED. Repetiu a marcação minimizado, preservando Groove manual e envio físico. Conferiu intensidade, próximo compasso, drop, silêncio e fechamento. [Relatório](resultado-pixel-midi-v0.40.0.json) · [Log](resultado-pixel-midi-v0.40.txt).

O teste separado de quatro saídas passou com comprimentos **120/300/90/120** nos GPIOs 18/19/25/26: quadro de 1.890 bytes, cópia exata, buffers reutilizados, minimização, blackout, reconexão reduzindo o pacote para 1.620 bytes, persistência e recarga. [Relatório](resultado-pixel-four-outputs-v0.40.0.json) · [Log](resultado-pixel-four-outputs-v0.40.txt).

## Ensaio de estabilidade nativo

**60 segundos reais com oito horas musicais aceleradas**, captura sintética e ESP32 emulado. Usa uma fita de 300 LEDs dividida em seis barras com três pares simétricos, modo único, marcação de referência e mudanças de estrutura.

Confirmou:

- zero blocos de áudio descartados;
- buffers de pixels/texturas/sinais com dimensões e alocações estáveis;
- até dois descritores no modo único, zero snapshots de misturas e histórico de até doze composições;
- cópias exatas durante as mudanças e dados RGB inteiros entre 0 e 255;
- gravações de projeto atrasadas artificialmente em 50 ms, com no máximo uma pendente;
- pausa de 450 ms no renderer desarmando a saída e descartando quadros vencidos;
- contador musical atravessando o máximo inteiro Qt e continuando pelo WebChannel real;
- reabertura da prévia mantendo áudio/projeto e exigindo nova ativação física;
- encerramento completo das threads e gravações.

Os relatórios registram amostras de RAM do processo principal, renderer e heap exposto pelo Chromium. Memória do renderer varia com aquecimento e coleta; os limites demonstrados são dos buffers/objetos monitorados, sem prometer uma cota fixa de RAM do Chromium.

[Relatório e amostras](resultado-pixel-endurance-v0.40.0.json) · [Log](resultado-pixel-endurance-v0.40.txt) · [Auditoria e comando de ensaio longo](auditoria-buffers-v0.40.md).

## Custo gráfico

Comparação com o HTML 0.39 no mesmo host, seed 1337, seis barras de 300 LEDs, raster 600 × 280, renderização por software e seis segundos medidos por fase. O intervalo foi mantido longo para conservar o padrão durante a medição. Sem hardware.

| Auto Show | 0.39 em camadas | 0.40 efeito único |
| --- | --- | --- |
| Padrão | Aurora + Maré + Onda Vertical | Aurora |
| FPS | 30,0 | 30,0 |
| Desenho médio | 2,14 ms | 1,54 ms |
| CPU do renderer | 19,3% | 13,5% |
| RAM residente do renderer | 196,4 MiB | 167,5 MiB |

A redução observada foi de aproximadamente **28% no tempo de desenho e 30% na CPU do renderer** ao isolar o padrão. CPU usa um núcleo como 100%; os valores não representam o aplicativo inteiro. A cena de controle Ondas orgânicas, já com um padrão, permaneceu em 30 fps e cerca de 1,82 ms por desenho nas duas versões. Não houve realocação dos buffers monitorados durante as fases.

[Referência](resultado-pixel-render-reference-v0.39.json) · [Efeito único](resultado-pixel-render-single-v0.40.json) · [Log](resultado-pixel-render-single-v0.40.txt).

## Distribuição e limites

Instalação editável e wheel são **0.40.0**. A verificação compara todas as fontes/recursos declarados, mantém byte a byte os **25 arquivos DSP/música/contratos** contra 0.39 e confere firmware e fontes. [Verificação](resultado-package-v0.40.json).

O firmware permanece **0.37.0**, para GPIOs 18, 19, 25 e 26. A atualização não exige regravação do ESP32. [Registro](resultado-esp32-v0.37.json) · [Validação anterior](validacao-v0.39.md).

Os dispositivos foram emulados. Tempo musical acelerado e ensaios curtos não equivalem a seis horas reais com Traktor, X1 e fitas físicas. Esse teste prolongado do conjunto real ainda não foi realizado nesta entrega.
