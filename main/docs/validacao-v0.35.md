# Validação — versão 0.35.0

Registro: **2026-11-01**. Saída do contínuo fixo e participação esporádica de contínuos no AUTO SHOW. Ensaios sintéticos, sem captura, Traktor, Link nativo ou ESP32 real.

## Regressão apropriada

**154 testes JavaScript passaram**, incluindo 16 casos novos. Cobrem os três caminhos de saída do contínuo fixo, restauração/persistência da direção regular, botões exclusivos, migração de projetos presos em AUTO/Contínuo, participação automática habilitada/desabilitada e duração mínima de 32 tempos. Exercitam Hipnótica e Variada com três fontes aleatórias constantes, para verificar entrada/saída sem contínuos consecutivos. Também verificam prioridade de build-up/drop, oito kicks, regras de manter padrão, variedade dos catálogos e memória limitada. [Log](resultado-pixel-js-v0.35.txt).

**131 testes Python passaram**, incluindo aceitação/rejeição dos novos campos, projetos, persistência, topologia, USB, confiabilidade e UI. [Log](resultado-pytest-v0.35.txt).

A análise musical não foi alterada e a suíte DSP completa não foi repetida. DSP, música e contratos são conferidos byte a byte contra o wheel 0.34. [Registro anterior](validacao-v0.34.md) · [Verificação do pacote](resultado-package-v0.35.json).

## Interface nativa e USB emulado

[validate_auto_continuous.py](../scripts/validate_auto_continuous.py) abre a aplicação Qt e uma serial emulada com uma fita de 300 pixels dividida em seis barras e cópias exatas. Injeta pacotes musicais sintéticos e avança o relógio por combinações; não representa minutos reais de apresentação.

O ensaio confirmou:

- AUTO SHOW, ORGÂNICO e o segundo clique em CONTÍNUO FIXO saem do modo mantido;
- o AUTO começa com um padrão regular quando selecionado explicitamente;
- três trechos contínuos apareceram entre 18 combinações, sem duas entradas consecutivas;
- os contínuos têm mínimo de 32 tempos e todos os pixels acesos após a fusão;
- AUTO SHOW permanece selecionado durante um contínuo ocasional, com CONTÍNUO FIXO desligado;
- desativar a participação é persistido no armazenamento nativo;
- geometria/conexões e buffers são conservados;
- saída continua minimizada e blackout/fechamento terminam com zero.

[Relatório](resultado-auto-continuous-v0.35.0.json) · [Log](resultado-auto-continuous-v0.35.txt) · [AUTO retomado](../preview-auto-retomado-v0.35.png) · [Contínuo ocasional](../preview-auto-continuo-ocasional-v0.35.png) · [Contínuo fixo](../preview-continuo-fixo-v0.35.png).

Registrou **21,32 fps** no final desse ensaio curto. O emulador registra payloads, sem reproduzir brilho/corrente/temporização elétrica; o resultado não certifica seis horas com hardware.

## Comportamento e distribuição

O problema era a direção Contínua persistir ao selecionar AUTO SHOW/ORGÂNICO. A nova saída restaura a direção regular guardada; projetos antigos sem essa informação voltam à Hipnótica. Uma combinação AUTO/Contínuo salva na versão anterior abre como AUTO regular.

`autoContinuous` recebe verdadeiro por padrão nos projetos antigos e pode ser desligado na interface. Cada entrada ocasional ocupa uma combinação, entre duas a quatro combinações regulares; não altera permanentemente a direção visual. Build-up/drop e as regras de troca conservam prioridade. A escolha só ocorre na criação de combinações, sem sorteios por quadro ou novos timers. Catálogos mantêm memórias separadas e limitadas.

Instalação editável e wheel são **0.35.0**. Fontes/recursos são comparados byte a byte ao pacote; DSP, música, contratos e firmware são conferidos contra a versão anterior. [Verificação](resultado-package-v0.35.json). Firmware 0.22 permanece compatível. [Instruções](auto-continuo-v0.35.md).
