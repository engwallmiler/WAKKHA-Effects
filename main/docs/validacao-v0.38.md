# Validação — versão 0.38.0

Registro: **2026-11-05**. Prévia otimizada, painéis PAR/moves desabilitados com reativação, MIDI Learn e retorno de LEDs. O firmware das quatro saídas continua sendo o **0.37.0**, sem necessidade de nova gravação para esta atualização.

## Regressão

**920 testes Python passaram na suíte completa**, sem skips, em 249,20 s. Inclui DSP, kicks/BPM/estrutura, configurações, UI, topologia, saída USB e sketch real com periféricos simulados. Depois, **40 testes MIDI/backend/interface passaram no reteste final**, incluindo três novos casos: encerramento durante a preparação da espera da thread, falha parcial de retorno LED e mudança do endereço durante teste LED. Os demais casos do reteste já pertenciam à suíte completa. [Resumo completo](resultado-pytest-v0.38.txt) · [Reteste MIDI](resultado-midi-tests-v0.38.txt).

**174 testes JavaScript passaram**, sem skips. Cobrem comandos manuais mantidos, modos que liberam a estrutura, drop imediato de oito tempos, troca no próximo compasso, sincronismo e correção de relógio, silêncio/isolamento USB, cadência da prévia e limite de amostragem de desenho. Conservam efeitos, cores, evolução, grupos, continuidade, picos e verificações de memória limitada anteriores. [Resumo](resultado-pixel-js-v0.38.txt).

O comparador de referência confirmou **140 quadros RGB idênticos em 35 modos**, usando o HTML 0.37 como referência. A redução de resolução é exclusiva da prévia; os LEDs físicos continuam individualizados. [Relatório](resultado-pixel-rgb-parity-v0.38.json).

## MIDI nativo com dispositivos emulados

[validate_pixel_midi.py](../scripts/validate_pixel_midi.py) abre a interface Qt/WebEngine, entrada/saída MIDI emuladas e quatro saídas ESP32 emuladas de 120 LEDs. Não abre X1, COM, captura ou Link físicos. Confirmou:

- Learn nas dez funções, primeiro endereço capturado, nenhum efeito durante Learn e salvamento somente após ação explícita;
- estruturas manuais mantidas e liberação pelo mesmo botão, outra estrutura ou modo;
- drop imediato por oito tempos, sincronismo 1/8 e nova combinação no próximo compasso;
- intensidade nos extremos de 0 e 100%, retorno LED pelo estado efetivo e ausência de filas crescentes;
- funcionamento MIDI e USB minimizado, reativação reversível dos painéis antigos, silêncio com todas as saídas escuras e fechamento com apagamento.

O teste registrou 56 mensagens recebidas, 35 retornos e quadros conjuntos de 1.440 bytes. As latências medidas são internas da emulação, sem representar USB MIDI real ou resposta elétrica da fita. [Relatório](resultado-pixel-midi-v0.38.0.json) · [Log](resultado-pixel-midi-v0.38.txt) · [Tela Learn](../preview-midi-learn-v0.38.png) · [Estrutura manual](../preview-midi-estrutura-v0.38.png).

Os testes adicionais cobrem botões por borda de pressão, três formatos de encoder relativo, ordem dos incrementos, fila limitada, retorno somente por mudança, perfil inválido/duplicado, salvamento fora da GUI com edições concorrentes, comandos de pico coalescidos, timeout do renderer, handles WinMM de 64 bits e retenção de callback quando um driver falha ao fechar.

## Quatro saídas USB

O ensaio nativo foi repetido com comprimentos **120/300/90/120** nos GPIOs **18/19/25/26**. Passaram: payload de 1.890 bytes, cópia física exata, reutilização de buffers, saída minimizada, blackout, reconexão omitindo a saída desabilitada (1.620 bytes), recarga da prévia, persistência e encerramento. Os fps desse ensaio incluem interações/recargas e não medem o desempenho do ESP32. [Relatório](resultado-pixel-four-outputs-v0.38.0.json) · [Log](resultado-pixel-four-outputs-v0.38.txt).

O sketch e o binário não foram alterados nem recompilados nesta rodada. A compilação e os hashes 0.37 continuam registrados: 359.456 bytes na imagem gravável, 29.920 bytes de RAM estática e 293.561 bytes de programa. O driver mantém oito slots RMT e dois blocos por transmissor para as quatro saídas. [Registro](resultado-esp32-v0.37.json) · [Validação 0.37](validacao-v0.37.md) · [Guia físico](esp32-quatro-saidas.md).

## Fluidez da prévia

Comparação controlada com a referência 0.37, mesmo host/seed, renderização por software, seis barras de 300 pixels e canvas de 600 × 280. Cada fase mede seis segundos, sem hardware:

| Cena | FPS 0.37 → 0.38 | Desenho médio 0.37 → 0.38 | CPU do renderer 0.37 → 0.38 |
| --- | --- | --- | --- |
| Auto: Aurora + Maré + Onda Vertical | 19,0 → 28,8 | 11,48 → 8,85 ms | 38,0 → 30,7% |
| Contínuo: Ondas orgânicas | 18,5 → 28,5 | 11,65 → 9,35 ms | 37,5 → 44,5% |

CPU considera um núcleo como 100%. O contínuo desenha mais quadros e consome mais CPU total nesta execução. Não houve novas alocações dos buffers monitorados ou erros. Os resultados demonstram maior fluidez e menor custo por desenho nesta máquina; não garantem uma taxa em outros equipamentos. [Referência](resultado-pixel-render-reference-v0.37.json) · [Atual](resultado-pixel-render-v0.38.json) · [Detalhes](otimizacao-pixel-v0.38.md).

## Pacote e limites

A instalação editável e o wheel são **0.38.0**. A verificação compara todas as fontes e recursos declarados ao wheel, conserva byte a byte os 25 arquivos DSP/música/contratos contra 0.37 e confere os hashes dos firmwares e suas fontes. [Verificação do pacote](resultado-package-v0.38.json).

Não houve ensaio desta entrega com X1 MK1, ESP32/fitas reais nem seis horas reais contínuas. Há ensaios acelerados de histórico/memória e validação causal/DSP na suíte, que não substituem esse teste físico prolongado. [Operação MIDI](midi-x1-mk1.md) · [Confiabilidade](confiabilidade.md).
