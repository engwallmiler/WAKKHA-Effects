# Validação — versão 0.39.0

Registro: **2026-11-05**. Organização com palco permanente, ajustes laterais, saída de tela cheia e otimizações de desenho/recursos. Nenhuma alteração nos detectores musicais ou no firmware.

## Regressão completa

**926 testes Python passaram**, sem skips, em **285,76 segundos**. Incluem DSP, kicks/BPM/estrutura, UI, MIDI, USB, topologia, persistência e execução do sketch com periféricos simulados. Três novos testes verificam F11/Esc/botão com foco em controles filhos, restauração da janela maximizada, redirecionamento de fullscreen do Chromium e navegação saindo de tela cheia. [Log completo](resultado-pytest-v0.39.txt).

**178 testes JavaScript passaram**, sem skips. Os novos casos cobrem suspensão de desenhos pretos, retomada por ativação, qualidade de prévia sem alterar os RGBs físicos ou buffers integrais, limite de 15 fps e recuperação de preferência local inválida. Os testes de apresentação verificam prévia mantida nos ajustes e pausa no modo leve/minimizado. Conservam efeitos, camadas, grupos, sincronismo, drops e verificações de memória limitada. [Log completo](resultado-pixel-js-v0.39.txt).

A comparação contra o HTML 0.38 confirmou **140 quadros RGB idênticos em 35 modos**. [Resultado](resultado-pixel-rgb-parity-v0.39.json).

## Interface nativa

O ensaio Qt/WebEngine abre a interface real, sem hardware. Confirmou palco dentro da área visível nas quatro abas, ausência de rolagem do documento principal, ajustes com rolagem própria e layout na janela mínima de 1100 × 760. F11, Esc e botão retornaram da tela cheia com foco dentro do WebEngine, restaurando a janela maximizada e a navegação lateral. Recarregar a prévia também saiu de tela cheia.

Foram conferidas imagens completas do canvas frontal, incluindo barras inclinadas e flashes, mantendo igualdade com o buffer composto. Nenhum erro JavaScript ocorreu e o encerramento foi concluído. [Relatório](resultado-pixel-workspace-v0.39.0.json) · [Log](resultado-pixel-workspace-v0.39.txt) · [Script](../scripts/validate_pixel_workspace.py) · [Palco](../preview-workspace-stage-v0.39.0.png) · [Edição](../preview-workspace-effects-v0.39.0.png).

## MIDI e USB

O ensaio integrado aprendeu as dez funções, preservou o Auto Show enquanto Learn suprimia intervenções MIDI, salvou explicitamente, conferiu modos manuais, sincronismo, próximo compasso, intensidade, LEDs e operação minimizada com quatro saídas emuladas. A emulação confirmou silêncio/fechamento com apagamento e filas limitadas. [Relatório](resultado-pixel-midi-v0.39.0.json) · [Log](resultado-pixel-midi-v0.39.txt).

O ensaio USB separado repetiu comprimentos **120/300/90/120** nos GPIOs **18/19/25/26**: payload conjunto de 1.890 bytes, cópia exata, buffers reutilizados, envio minimizado, blackout, reconexão reduzindo o payload para 1.620 bytes, persistência e recarga. [Relatório](resultado-pixel-four-outputs-v0.39.0.json) · [Log](resultado-pixel-four-outputs-v0.39.txt).

## CPU, memória e fluidez

Comparação com o HTML 0.38 no mesmo host Python, semente 1337, seis barras de 300 LEDs e raster de 600 × 280, renderização por software e seis segundos medidos por fase. Sem áudio, MIDI ou USB físicos.

| Cena | FPS 0.38 → 0.39 | Desenho médio | CPU renderer | RAM residente renderer |
| --- | --- | --- | --- | --- |
| Auto | 28,5 → 30,0 | 8,81 → 2,41 ms | 43,2 → 13,3% | 247,6 → 194,7 MiB |
| Ondas orgânicas | 28,3 → 30,0 | 9,22 → 2,30 ms | 47,1 → 25,8% | 248,8 → 197,5 MiB |

CPU usa um núcleo como 100%. A memória indicada pertence somente ao renderer; os relatórios também registram o processo principal. A redução não deve ser interpretada como percentual do consumo total do computador. Os valores variam com carga, máquina e coleta de memória.

Em Econômica, a prévia de ondas ficou em 15 fps, 1,65 ms/desenho e CPU de 17,2%. Sem emissão, após o quadro inicial de apagamento, não houve novos desenhos, contra 28,7 fps na referência; CPU passou de 38,8 para 6,8%. Minimizado não houve desenhos e a CPU do renderer ficou em 0% no período. Os buffers monitorados não foram realocados durante as fases e não houve erros JavaScript.

[Referência 0.38](resultado-pixel-render-reference-v0.38.json) · [Atual 0.39](resultado-pixel-render-v0.39.json) · [Log](resultado-pixel-render-v0.39.txt) · [Operação e limites](interface-pixel-v0.39.md).

## Distribuição e limites

Instalação editável e wheel são **0.39.0**. A verificação compara todas as fontes/recursos declarados, mantém byte a byte os **25 arquivos DSP/música/contratos** contra 0.38 e confere o firmware 0.37 e suas fontes. [Verificação](resultado-package-v0.39.json).

O firmware das quatro saídas permanece **0.37.0**, com 359.456 bytes na imagem gravável e o mesmo hash registrado anteriormente. Não é necessário regravar o ESP32 para esta atualização. [Registro](resultado-esp32-v0.37.json) · [Validação anterior](validacao-v0.38.md).

Os dispositivos foram emulados. Não houve teste desta entrega com X1/ESP32 físicos nem seis horas reais contínuas. Os ensaios acelerados de histórico e os testes causais não substituem esse teste prolongado. [Confiabilidade](confiabilidade.md).
