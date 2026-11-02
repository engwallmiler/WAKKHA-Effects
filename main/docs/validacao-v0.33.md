# Validação — versão 0.33.0

Registro: **2026-11-01**. Picos de fita inteira e apresentação contínua, com o mesmo amostrador na prévia e no USB. Nenhum áudio, Link nativo ou ESP32 físico foi utilizado.

## Testes apropriados à mudança

**122 testes JavaScript passaram**, incluindo 31 casos novos. Verificam os 300 pixels em branco máximo no pico, intensidade monotônica, 0% sem alterar o padrão/preparação, sustentação para saída próxima de 21 fps, onda/blocos, brilho mestre/individual, cor escolhida, blackout, fita desativada, silêncio e dados vencidos. Os quatro efeitos contínuos mantêm todos os pixels acesos, mudam cores e evoluem suavemente. As combinações duram pelo menos 32 tempos e preservam cópias exatas/continuidade. Os 30 efeitos compartilham valores RGB entre prévia e amostragem física. [Log](resultado-pixel-js-v0.33.txt).

**125 testes Python passaram** sobre projetos, topologia, transporte USB, persistência, confiabilidade e UI. Incluem aceitação/rejeição dos novos controles e gravação pelo armazenamento nativo. [Log](resultado-pytest-v0.33.txt).

A suíte DSP completa não foi repetida: os arquivos de DSP, música e contratos são conferidos byte a byte contra o wheel 0.32 na verificação do pacote. O [registro 0.32](validacao-v0.32.md) conserva os testes e limites da detecção.

## Canvas nativo e transporte emulado

[validate_pixel_peaks.py](../scripts/validate_pixel_peaks.py) usa a aplicação Qt e uma serial emulada, com uma fita WS2812 de 300 pixels dividida em seis barras e cópias exatas. Injeta pacotes musicais sintéticos; a fase é mantida dentro do acento para conferir os quadros. Não mede a duração de um pico em música real.

O ensaio verifica:

- crescimento de brilho nos níveis 0/25/50/75/100%;
- em 100%, os 900 bytes RGB do Clarão chegam a 255 com brilho mestre/individual em 100%;
- Onda e Blocos com regiões no máximo e quadros distintos;
- base contínua com todos os pixels acesos após a fusão de entrada;
- persistência dos controles no armazenamento nativo;
- buffers/texturas reutilizados, saída continuando minimizada e zero no blackout/encerramento.

[Relatório](resultado-pixel-peaks-v0.33.0.json) · [Log](resultado-pixel-peaks-v0.33.txt) · [Clarão](../preview-pico-maximo-v0.33.png) · [Contínuo](../preview-continuo-v0.33.png).

A medição final de fps consta no relatório e varia durante interação/capturas. O emulador registra o payload RGB, sem simular a limitação elétrica ou o brilho real da fita. Brilho mestre, brilho individual e os limites do firmware continuam relevantes. O ensaio curto não certifica seis horas contínuas ou temporização elétrica do ESP32.

## Operação e distribuição

Picos recebem controles de desenho (Clarão/Onda/Blocos) e cor (Branco/Cores da apresentação). Projetos anteriores recebem Clarão/Branco como padrões. A intensidade continua persistida de 0 a 1; mudou sua resposta visual, com uma camada independente da máscara e do drive do padrão. O máximo respeita os tetos configurados.

A direção Contínua é opcional e pode ser ativada pelo botão **CONTÍNUO**. Reutiliza evolução, relógio, paletas e envelopes existentes, conservando uma base preenchida. As respostas de fita guardadas no projeto voltam a operar normalmente nos demais efeitos. Os drops mantêm prioridade própria.

Instalação editável e wheel são **0.33.0**. Fontes/recursos são comparados byte a byte ao pacote; DSP, música, contratos e firmware são conferidos contra a versão anterior. [Verificação](resultado-package-v0.33.json). O firmware 0.22 não precisa ser regravado. [Instruções](picos-continuos-v0.33.md).
