# Validação — versão 0.42.0

Registro: **2026-11-06 UTC**. Referência de compassos reversível e duração de drop por oito tempos estimados pelo BPM. Os critérios de identificação de kick e entrada do drop foram preservados.

**963 testes Python passaram**, sem skips, em **484,25 segundos**, cobrindo DSP, estrutura, identificação de kicks, UI, MIDI, USB, projetos e firmware com periféricos simulados. [Log completo](resultado-pytest-v0.42.txt).

## Motor visual e testes de duração

**210 testes JavaScript passaram**, sem skips, em **7,55 segundos**. Os novos casos cobrem:

- Drop automático a 90, 120, 128, 150 e 180 BPM, sem novas confirmações de kick.
- Muitas confirmações não encurtam a apresentação; contagem parada não a prolonga.
- Fallback ao último BPM quando a grade falta temporariamente.
- Idade do impacto, pacotes expirados, mesmo identificador sem reinício e novo drop permitido.
- Correções de grade, troca áudio/Link e Sincronizar 1/8 preservando duração restante.
- Progressão visual idêntica com confirmação acústica esparsa ou regular.
- Marcar/desmarcar pela interface e MIDI, inclusive sem grade para cancelar.
- Nova estrutura de breakdown interrompendo a cena, sem esperar o prazo.

[Log JavaScript](resultado-pixel-js-v0.42.txt).

Os **86 testes direcionados Python de estrutura e ponte de pixels passaram** em **1,99 segundo**, incluindo os cenários que antes exigiam esperar oito confirmações acústicas. Os casos agora verificam fim pelo BPM com confirmação ausente/esparsa e preservação da contagem real. [Log](resultado-drop-tests-v0.42.txt).

## Interface e MIDI reais, periféricos emulados

Qt/WebEngine, quatro saídas USB emuladas de 120 pixels e MIDI emulado. O ensaio aprendeu onze funções, preservou os perfis e conferiu retorno dos LEDs. O comando de referência **desmarcou e marcou novamente com a janela minimizada**, apagando/acendendo o LED correspondente.

O drop automático terminou ao avançar oito tempos da grade mesmo mantendo **drop_kicks = 1**, sem eventos acústicos adicionais. Continuou por 7,5 tempos, encerrou ao ultrapassar oito, apagou o LED do drop e não reiniciou com o mesmo identificador. O teste também preservou o drop manual de oito tempos, saída USB minimizada, silêncio e fechamento. [Relatório MIDI/USB](resultado-pixel-midi-v0.42.0.json) · [Log](resultado-pixel-midi-v0.42.txt).

O ensaio de interface conferiu clique real no botão **Marcar → Desmarcar → Marcar**, estado aria-pressed e referência interna. Preservou palco visível nas abas, janela mínima de 1100 × 760, editor de 33 efeitos e retorno de tela cheia por Esc/F11/botão/recarga. Não houve erro JavaScript. [Relatório](resultado-pixel-workspace-v0.42.0.json) · [Log](resultado-pixel-workspace-v0.42.txt).

## Compatibilidade e distribuição

**140 quadros físicos em 35 modos conservaram o RGB exato** frente à versão 0.41 na comparação em demonstração. A apresentação de drop ao vivo muda intencionalmente: pulsos, evolução e término passam a seguir os tempos estimados, com testes próprios. [Comparação](resultado-pixel-rgb-parity-v0.42.json).

A mudança na análise musical fica restrita a **music/structure.py**, no prazo do drop e seu texto diagnóstico. O pacote registra os hashes dessa alteração e compara os outros **24 arquivos DSP/música/contratos** byte a byte. Identificação de kick, estimador de BPM, características espectrais, evidências de entrada do drop, firmware e fontes do ESP32 permanecem preservados. [Verificação](resultado-package-v0.42.json).

Instalação editável e wheel são **0.42.0**. O firmware segue **0.37.0**, GPIOs 18/19/25/26; não exige regravação. Não foram acrescentados threads, FFTs ou históricos para essa duração. O pacote musical ganhou apenas a idade opcional do impacto. [Operação](drop-bpm-e-referencia-v0.42.md) · [Entrega anterior](validacao-v0.41.md).

Não foram utilizados ESP32, fitas ou X1 físicos nos ensaios. Esta rodada não certifica seis horas reais de operação nem melhora, por si, a acurácia do detector de kicks; impede que suas falhas prolonguem a apresentação de drop.
