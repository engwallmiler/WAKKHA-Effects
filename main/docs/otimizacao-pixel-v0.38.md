# Fluidez e MIDI — 0.38.0

Esta rodada reduz trabalho por quadro, corrige a agenda da prévia e acrescenta MIDI com filas limitadas. O motor de efeitos e as quatro saídas físicas continuam compartilhando o mesmo cálculo RGB.

## Comparação da prévia

Ensaio Qt/WebEngine com renderização por software, seis barras de 300 LEDs, canvas de 600 × 280, mesma semente aleatória e seis segundos medidos por fase. A referência é o HTML do pacote 0.37; ambos rodam no mesmo host Python. Sem áudio ou USB físicos.

| Cena | Prévia 0.37 | Prévia 0.38 | Tempo médio de desenho antes → depois |
| --- | --- | --- | --- |
| Auto: Aurora + Maré + Onda Vertical | 19,0 fps | 28,8 fps | 11,48 → 8,85 ms |
| Contínuo: Ondas orgânicas | 18,5 fps | 28,5 fps | 11,65 → 9,35 ms |

O limite continua em **30 fps**. A correção de prazos evita perder quadros por pequenas diferenças em torno de 33,3 ms. São resultados deste ensaio curto; variam com máquina e carga.

CPU do renderer, considerando um núcleo como 100%: Auto **38,0 → 30,7%**; contínuo **37,5 → 44,5%**. O contínuo produz mais quadros e consome mais CPU total nesta medição, apesar do menor custo por desenho. Não há redução universal de CPU.

[Referência](resultado-pixel-render-reference-v0.37.json) · [Atual](resultado-pixel-render-v0.38.json) · [Script](../scripts/benchmark_pixel_render.py).

## Cálculo e resolução

- Envelopes de kick, pico e contínuo são calculados uma vez por quadro, compartilhados pelos pixels.
- A transformação de brilho da prévia usa tabela reutilizável. Indicadores HTML atualizam até cinco vezes por segundo. A posição do canvas fica em cache por até 250 ms, invalidado ao rolar/mudar layout.
- A prévia embutida amostra até **192 pontos por barra**; o HTML independente usa até 384. Barras menores mantêm todos os pontos. Essa resolução é exclusiva do desenho e pode suavizar detalhes menores que um ponto da prévia.
- A saída física continua calculando **cada LED individual**, sem reduzir endereços ou dados enviados. Foram comparados **140 quadros RGB em 35 modos**, com igualdade exata frente à 0.37. [Comparação](resultado-pixel-rgb-parity-v0.38.json).
- A composição segura da imagem mantém o buffer de tela, preservando a correção anterior das piscadas. Texturas e buffers são reutilizados.

## Segundo plano e painéis antigos

**Lighting Studio e Stage Preview vêm desabilitados**, sem iniciar o worker PAR/moves. Reative em **Configurações → Habilitar Lighting Studio e Stage Preview · PAR/moves**. A preferência é salva imediatamente. Desabilitar novamente oculta as páginas e suspende o worker; código e preferências anteriores permanecem disponíveis.

**Apresentação leve** e minimização continuam pausando palco e gráficos. Páginas de análise só desenham quando visíveis, com janela restaurada e modo leve desligado. A FFT usada na análise musical continua necessária. Captura, Link, efeitos e USB permanecem ativos. A tabela MIDI só atualiza na sua página visível, até quatro vezes por segundo.

O WebEngine continua hospedando o motor mesmo sem desenho. Uma falha desse renderer exige **Reabrir prévia** e nova ativação física.

## MIDI e encerramento

O callback nativo recebe mensagens curtas numa fila de até 512 eventos. Clock MIDI, Active Sensing e mensagens não utilizadas são ignorados antes da fila. O driver roda fora da interface; a thread dorme enquanto não há retorno LED para enviar. Só diferenças de estado são transmitidas, até dez endereços.

A entrada é consumida a cada 20 ms quando conectada, mesmo minimizada. Incrementos relativos são preservados; o último nível substitui ajustes pendentes. Até 64 comandos podem aguardar, com uma chamada JavaScript ativa. Sem resposta em 500 ms, novas chamadas são bloqueadas até reabrir a prévia. Gestos antigos não são repetidos automaticamente.

Perfis são validados e gravados atomicamente fora da interface. Learn descarta gestos antigos nas fronteiras de entrada/saída e não executa efeitos. O fechamento aguarda gravação iniciada e encerramento MIDI; callbacks nativos permanecem vivos até o driver liberar a porta. O USB conserva sua fila de quadro mais recente.

Ensaios emulados verificam Learn, salvamento, botões mantidos, LEDs, quatro saídas, minimização e encerramento. Não houve teste com X1 MK1 real nem seis horas reais nesta entrega. [Resultados](validacao.md) · [Operação MIDI](midi-x1-mk1.md).
