# Fita física de 120 LEDs — Pixel Studio 0.36

A saída agora aceita uma fita lógica com **1 a 300 LEDs WS2812/WS2812B individuais**. A versão anterior exigia exatamente 300 LEDs e o botão de preparação substituía a resolução do projeto por 300. Isso bloqueava o envio de uma fita configurada corretamente com 120 LEDs.

## Usar sua fita de 120 LEDs

1. Feche e abra novamente o aplicativo pelo **iniciar.cmd**. O cabeçalho deve mostrar **v0.36**.
2. Selecione **Saída física · ESP32 USB** e abra a configuração da fita.
3. Escolha sua fita na lista. Confira **LEDs na fita física: 120**. O campo recebe a quantidade do projeto selecionado.
4. Clique **Preparar fita WS2812**. O painel identifica a fita preparada. Nome, coordenadas, metragem, identidade, controles e conexões são mantidos; cada LED recebe um pixel individual. Se o total já é 120, cada trecho conserva sua quantidade de LEDs.
5. Selecione a COM do ESP32 e clique **Conectar ESP32**, caso ainda esteja desconectado. Depois clique **Ativar saída física**.
6. Para conferir sem música, selecione **Demonstração · sem áudio** na prévia. Para acompanhar o Traktor, use a entrada ao vivo com áudio ativo. O estado **TRANSMITINDO** e o contador de quadros indicam envio confirmado.

**Não é necessário regravar o ESP32.** O firmware 0.22 continua recebendo quadros de 300 endereços. Os primeiros 120 contêm os efeitos do projeto; os outros 180 recebem zero em todos os quadros, inclusive ao trocar de uma fita de 300 para uma menor. Não há reamostragem para preencher 300 LEDs nem alteração dos tempos dos efeitos.

Se a fita for dividida em barras, selecione a **fita lógica contínua**: a soma dos LEDs dos seus trechos deve corresponder à fita física. A quantidade indicada no painel vale para o cabo inteiro. Ao escolher outro total, a preparação redistribui os endereços entre os trechos; as demais fitas não são redimensionadas.

Cópias exatas continuam exigindo resoluções e formatos compatíveis. Se a preparação quebrar essa relação, ela apresenta o motivo e conserva o projeto anterior. Ajuste os trechos envolvidos ou use a adaptação de resolução. A preparação não remove grupos para contornar o conflito.

Preparar e conectar mantêm a saída apagada; ativar é uma ação separada. Simulação, blackout, silêncio, perda de dados e fechamento mantêm as proteções existentes. O teto permanece em 300 LEDs por saída nesta versão. Os limites de brilho/corrente e a ligação elétrica continuam descritos no [guia do ESP32](esp32-ws2812-usb.md).

## Verificação

O [ensaio nativo](../scripts/validate_pixel_strip_size.py) usa serial emulada: prepara 120 LEDs, confirma valores RGB e endereços restantes apagados, alterna 300 → 120, minimiza, reabre a prévia e verifica persistência e blackout. [Resultados](resultado-pixel-strip-size-v0.36.0.json). Não foi conectado hardware durante esse ensaio.
