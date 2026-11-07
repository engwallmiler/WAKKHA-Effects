# Validação — versão 0.44.1

Registro: **2026-11-07 UTC**. Ampliação do seletor de repetição do pico para **4, 8, 16 e 32 tempos**, com aceitação no projeto JavaScript e na persistência Python.

**76 testes Python direcionados passaram** em **0,74 segundo**, incluindo gravação e leitura dos quatro intervalos e rejeição de valores não suportados. [Log](resultado-pixel-tests-v0.44.1.txt).

**234 testes JavaScript passaram**, sem skips, em **7,99 segundos**. O teste do pico agora cobre os quatro intervalos: referência sem alterar BPM, ausência de acento no meio do ciclo, pico na posição esperada e prioridade do blackout. [Log](resultado-pixel-js-v0.44.1.txt).

A comparação contra o wheel 0.44 confirma **93 módulos Python preservados**, considerando em `ui/window.py` somente a troca do texto da versão. No HTML, mudaram somente as opções do seletor e sua validação de projeto. O cálculo de sincronização, intensidade, efeitos, captura, detecção, Link, MIDI e saída USB foi preservado; a participação automática continua com seus intervalos anteriores. [Registro](resultado-picos-longos-v0.44.1.json).

A instalação editável e o wheel são **0.44.1**. A verificação compara fontes e recursos do pacote, os 25 arquivos DSP/música/contratos e hashes de firmware contra a entrega anterior. [Pacote](resultado-package-v0.44.1.json).

Não foi repetido o ensaio prolongado nem utilizado hardware nesta alteração de opções. Os resultados gerais da 0.44 estão [arquivados](validacao-v0.44.md). [Como usar e unidade de contagem](picos-longos-v0.44.1.md).
