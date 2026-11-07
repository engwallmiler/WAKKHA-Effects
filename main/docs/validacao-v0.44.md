# Validação — versão 0.44.0

Registro: **2026-11-07 UTC**. Modo Manual explícito, navegação no palco e seis padrões novos. O operador relatou duas horas sem interrupções na 0.43; esta rodada concentra mudanças nos controles, validação do projeto e catálogo de desenhos.

## Preservação e testes automatizados

**93 módulos Python foram preservados** contra o wheel 0.43, incluindo captura, fila de áudio, DSP, BPM, kicks, estrutura, Link, MIDI, USB, idade dos quadros e gravação assíncrona. `ui/window.py` recebeu somente a identificação da versão. Os trechos JavaScript de emissão, amostragem física, validade do áudio e política de renderização também foram comparados. [Registro](resultado-core-preservado-v0.44.json).

**992 testes Python passaram**, sem skips, em **471,65 segundos**. Incluem validação e persistência das novas seleções, rejeição de projetos inconsistentes e proteção do projeto anterior. [Log](resultado-pytest-v0.44.txt).

**234 testes JavaScript passaram**, sem skips, em **7,01 segundos** na execução final. Incluem entrada/saída do Manual, catálogo de 39 desenhos, percurso cíclico, memória da seleção, restauração das configurações individuais, manutenção diante de estruturas detectadas e saída por sete modos. Navegar 1.500 vezes mantém no máximo dois descritores, sem snapshots. Os seis desenhos são animados e limitados por pixel; cópias, sentido invertido e amostragem física/prévia foram conferidos. [Log](resultado-pixel-js-v0.44.txt).

**140 quadros em 35 modos antigos mantiveram RGB físico idêntico** contra a 0.43. As novas opções não ampliam silenciosamente um repertório personalizado já salvo. [Comparação](resultado-pixel-rgb-parity-v0.44.json).

## Interface nativa, MIDI e quatro saídas emuladas

Qt/WebEngine real com configurações temporárias, sem utilizar COM/MIDI/áudio físicos ou preferências do operador:

- Interface mínima de 1.100 × 760, painel de ajustes, botões anterior/próximo, catálogo e referência de compassos. Retorno da tela cheia por Esc, F11 e botão, além da recarga. [Relatório](resultado-pixel-workspace-v0.44.0.json).
- Onze funções MIDI existentes, Learn, gravação explícita, retorno dos LEDs e referência. Os comandos dos outros modos saem do Manual. Drop continua imediato e termina em oito tempos, mesmo com contador de kicks parado em 1. [Relatório](resultado-pixel-midi-v0.44.0.json).
- Seis padrões novos no Manual, seleção pelo dropdown, anterior/próximo, alterações detectadas de estrutura sem tomar o controle, quatro saídas de 120 LEDs, quarta copiando a primeira, operação minimizada e exportação válida. **780 blocos de áudio, zero descartes, 174 quadros USB, nenhum erro JavaScript** no último ensaio. Navegação visível também com o painel USB aberto: altura 38 px, limite inferior 294 px em viewport de 340 px. [Relatório](resultado-manual-patterns-v0.44.0.json) · [Log](resultado-manual-patterns-v0.44.txt).

O novo roteiro nativo inicialmente capturava uma imagem completa da janela e gravava uma exportação síncrona enquanto media áudio. Houve descartes nas tentativas iniciais, inclusive em uma repetição isolada. A instrumentação posterior não encontrou processamento de áudio acima de 25 ms e mostrou uma execução sem descartes durante todos os seis padrões, seguida de quatro descartes no trecho final. A imagem e a exportação de teste foram movidas para depois da medição/captura; o produto conserva seu gravador assíncrono. As duas execuções finais passaram com zero descartes. Isso não estabelece a causa de todos os descartes iniciais nem motivou alterar filas, análise ou transporte do aplicativo.

## Regressões de segurança e estabilidade

A verificação de idade dos quadros passou novamente com prévia visível, modo leve desligado, camadas, build-up a 127 BPM e quatro saídas de 120 pixels. Esperas de 400/594/594 ms antes da geração retomaram sem rearmar; entrega de RGB realmente antigo foi rejeitada. Bloqueio persistente de 1.100 ms exigiu reativação; apagamento manual não foi desfeito por callback posterior. **518 blocos de áudio, zero descartes, nenhum erro JavaScript**. [Relatório](resultado-frame-freshness-v0.44.0.json) · [Log](resultado-frame-freshness-v0.44.txt).

O ensaio de **60 segundos reais / oito horas musicais aceleradas** passou com **5.626 blocos de áudio, zero descartes, 1.244 quadros USB e 21,34 fps** ao final. Buffers estáveis, 30 gravações do projeto e zero escritas de diagnóstico perdidas. Inclui bloqueio persistente, reativação, rollover Qt, recarga com áudio e projeto preservados e encerramento dos workers. [Relatório](resultado-pixel-endurance-v0.44.0.json) · [Log](resultado-pixel-endurance-v0.44.txt).

O pacote e a instalação editável são **0.44.0**. A verificação confere fontes e recursos, os **25 arquivos DSP/música/contratos** contra 0.43 e hashes do firmware e suas fontes. [Verificação](resultado-package-v0.44.json). O firmware permanece **0.37.0**, GPIOs 18/19/25/26, sem regravação. [Entrega anterior](validacao-v0.43.md) · [Operação do Manual](manual-e-padroes-v0.44.md).

Acelerar o relógio musical não equivale a oito horas reais. Não foi feito nesta entrega um ensaio prolongado com ESP32, X1 e fitas físicos. As proteções de silêncio, dados antigos, apagamento manual, falha persistente e watchdog foram mantidas.
