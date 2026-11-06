# Pixel Studio — palco permanente e recursos

A versão **0.39.0** mantém o palco visível durante a edição. As abas **Efeitos e cores**, **Fitas e grupos** e **Biblioteca e drops** abrem ajustes ao lado dele, com rolagem própria. **Palco** ou **Fechar ajustes** devolvem toda a largura à prévia. Abrir painéis, trocar estrutura musical ou rolar os campos não empurra mais o palco para fora da janela.

Os controles AUTO SHOW, ORGÂNICO, CONTÍNUO FIXO, sincronismo, pico e blackout ficam junto da prévia. Os ajustes de simulação, fonte musical, importação/exportação e biblioteca ficam na aba Biblioteca e drops. **Simular · sem USB** continua acessível junto do palco. O seletor de entrada musical aparece uma vez; o drop nativo permanece no cabeçalho do aplicativo. Controles existentes foram reorganizados, preservando efeitos, projetos e mapeamentos MIDI.

[Palco](../preview-workspace-stage-v0.39.0.png) · [Ajustes ao lado da prévia](../preview-workspace-effects-v0.39.0.png) · [Janela de 1100 × 760](../preview-workspace-compact-v0.39.0.png).

## Tela cheia

No aplicativo, use **Tela cheia · F11**. Para voltar, pressione **Esc**, **F11** novamente ou **Sair da tela cheia · Esc** no cabeçalho. A navegação lateral retorna e uma janela anteriormente maximizada volta maximizada. O teclado funciona também com foco dentro do WebEngine ou em um controle.

O aplicativo controla a janela nativa, evitando que somente o canvas entre em tela cheia e esconda a saída. Reabrir a prévia ou navegar para outra página também sai da tela cheia. No HTML aberto diretamente no navegador, a área ampliada inclui um botão de saída sobre o palco; Esc continua disponível.

## Qualidade da prévia

O seletor no canto inferior da prévia afeta somente a imagem na tela:

| Opção | Desenho embutido | Pontos por barra | Limite |
| --- | --- | --- | --- |
| Fluida | 600 × 280 | até 128 | 30 fps |
| Econômica | 480 × 224 | até 80 | 15 fps |
| Detalhada | 900 × 420 | até 256 | 30 fps |

Com ajustes abertos, a prévia lateral usa até **15 fps**, conservando recursos para editar. Fechar os ajustes restaura o limite escolhido. A opção fica na preferência local da prévia, sem modificar o projeto ou os efeitos. Barras pequenas conservam todos os pontos; detalhes menores que um ponto da prévia podem ser suavizados na tela.

**Cada LED físico continua recebendo seu RGB individual**, inclusive com a qualidade Econômica, a janela minimizada ou Apresentação leve. Velocidade musical, BPM, MIDI e a transmissão USB não usam esse limite de desenho. A prévia continua sem difusão/halo das fitas.

## Trabalho eliminado

As texturas da prévia usam uma coluna de cor por barra, substituindo nove colunas repetidas. Os buffers físicos permanecem integrais. No projeto medido, as texturas passam de 41.472 para 3.072 bytes em Fluida; a economia de memória das texturas é pequena em termos absolutos, mas reduz o trabalho repetido por quadro.

O desktop agenda o desenho por prazo, sem depender da cadência de requestAnimationFrame do compositor por software. Há apenas um timer de prévia pendente. A composição continua produzindo um quadro completo no canvas frontal, preservando a correção das piscadas anteriores.

Sem emissão, o palco desenha o quadro apagado uma vez e suspende os desenhos repetidos. Controles/estado continuam atualizando em baixa frequência. Áudio recente ou ativação retomam a prévia. **Apresentação leve**, outra página e minimização continuam suspendendo o desenho; captura, análise, Link, MIDI e saída física permanecem independentes.

## Medição nesta máquina

Comparação com o HTML 0.38 no mesmo host, seis barras de 300 LEDs, mesma semente, canvas de 600 × 280, renderização por software e seis segundos por fase. Sem hardware físico:

| Cena | FPS 0.38 → 0.39 | Desenho médio | CPU do renderer | RAM residente do renderer |
| --- | --- | --- | --- | --- |
| Auto | 28,5 → 30,0 | 8,81 → 2,41 ms | 43,2 → 13,3% | 247,6 → 194,7 MiB |
| Ondas orgânicas | 28,3 → 30,0 | 9,22 → 2,30 ms | 47,1 → 25,8% | 248,8 → 197,5 MiB |

CPU considera um núcleo como 100%. A memória acima pertence ao renderer, não ao aplicativo inteiro ou ao Traktor. Em Econômica, as ondas ficaram em 15 fps e CPU de 17,2%. Sem emissão, houve zero desenhos após o apagamento inicial, contra aproximadamente 29 fps antes; a CPU medida passou de 38,8 para 6,8%. Minimizado, não houve desenhos e a CPU do renderer ficou em 0% no intervalo medido.

São ensaios curtos, sujeitos a variação de máquina, carga e coleta de memória; não certificam seis horas reais nem o fps elétrico das fitas. [Referência](resultado-pixel-render-reference-v0.38.json) · [Atual](resultado-pixel-render-v0.39.json) · [Validação funcional](validacao.md).

O firmware continua sendo **0.37** para GPIOs 18, 19, 25 e 26. Não é necessário regravar o ESP32 para esta atualização.
