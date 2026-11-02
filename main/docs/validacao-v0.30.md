# Validação — versão 0.30.0

Registro: **2026-10-30**. Direção visual do Pixel Studio: 12 desenhos de drop, 14 famílias, memória por estrutura e cores musicais. Nenhum áudio, Link nativo ou porta COM físicos foram utilizados. Os motores de detecção, replay e firmware permanecem sem alterações nesta rodada.

## Regressão apropriada à mudança

**91 testes JavaScript passaram** no motor de pixels. Incluem 12 desenhos antes de reutilizar o catálogo, sorteio constante, retornos a groove/breakdown/build-up, combinações/paletas diferentes da entrada anterior, oito kicks reais, uma única fita de 300 pixels, trajetórias diferentes, respeito a cores fixas, cópias exatas e igualdade entre RGB da prévia e do envio físico. Uma sequência longa verifica memória limitada e manutenção do mínimo de 32 tempos. [Log](resultado-pixel-js-v0.30.txt).

**125 testes Python passaram** sobre projetos, topologia, confiabilidade, transporte USB, controles nativos, captura e interface Link. Validam também os novos controles booleanos e sua persistência. A suíte DSP completa da 0.29 não foi repetida nesta rodada; os arquivos de análise musical são conferidos byte a byte contra o wheel anterior na verificação do pacote. [Log desta rodada](resultado-pytest-v0.30.txt) · [Registro 0.29](validacao-v0.29.md).

## Integração Qt e USB emulado

[validate_pixel_direction.py](../scripts/validate_pixel_direction.py) usa a aplicação nativa, Canvas e o transporte serial emulado. Não abre uma placa real. O projeto possui uma fita WS2812 de 300 pixels dividida em seis barras, com cópias exatas. O ensaio verificou:

- doze nomes/desenhos e doze quadros RGB distintos;
- troca de família, combinação e paleta na volta a cada contexto;
- reutilização dos mesmos buffers durante os drops;
- continuidade da geração com a janela minimizada;
- blackout com pixels zerados e apagamento no encerramento;
- aproximadamente 21 quadros por segundo no final do ensaio.

As fontes de contexto são pacotes sintéticos na sessão de teste; não são classificações de faixas reais. O número de fps é de uma execução curta e varia durante interação/capturas da interface. Não prova desempenho elétrico, consumo de toda a festa ou estabilidade por seis horas.

[JSON completo](resultado-pixel-direction-v0.30.0.json) · [Log](resultado-pixel-direction-v0.30.txt) · [Primeira variante](../preview-drop-variant-1-v0.30.png) · [Segunda](../preview-drop-variant-2-v0.30.png) · [Terceira](../preview-drop-variant-3-v0.30.png).

## Persistência e limites

Projetos antigos recebem `dropVariety: true` e `musicColors: true` ao abrir no motor; desligar esses controles fica registrado no projeto. Geometria, continuidades e cópias são preservadas. Cor fixa, espectro RGB e paletas individuais conservam prioridade. O RGB físico e a simulação usam a mesma amostragem; não há alteração do limite de brilho/corrente ou do canal W.

O catálogo finito é reutilizado depois de percorrido; a garantia é não repetir imediatamente o desenho de drop anterior, e evitar a combinação/paleta principal da visita anterior de cada estrutura nos modos automáticos. Dentro de uma estrutura estável os motivos continuam repetitivos, com evolução gradual, em vez de sortear uma apresentação nova em cada kick.

## Distribuição

Instalação editável, wheel **0.30.0**, comparação byte a byte de fontes e recursos, compilação, ajuda dos comandos e identidade do firmware são verificadas em [resultado-package-v0.30.json](resultado-package-v0.30.json). O firmware 0.22 continua idêntico; não é necessário regravar o ESP32. [Operação dos novos efeitos](direcao-visual-v0.30.md).
