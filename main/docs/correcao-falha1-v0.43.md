# Apagamento registrado em falha1.json — correção 0.43

## O que o arquivo permite afirmar

O incidente foi registrado em **2026-11-06, 23:29:14.349 UTC**, correspondente a **20:29:14.349 −03:00** no arquivo. A versão era 0.42 e a janela estava visível, com Apresentação leve desligada, conforme informado pelo operador.

O motivo imediato foi `output.frame_timeout`: o computador ficou **781 ms sem aceitar um quadro** e desarmou a saída. Naquele instante:

- USB em `connected`, sem erro de transporte registrado; firmware 0.37.0.
- Quatro saídas de 120 pixels; a quarta repetia a primeira.
- **11.056 quadros confirmados**; havia cinco apagamentos temporários por falta de quadros recentes nos segundos anteriores.
- Captura de áudio em funcionamento, **zero blocos descartados**, fila vazia e dados recentes.
- Auto Show em camadas, build-up a 127 BPM; último desenho registrado em 1,3 ms.
- Última resposta de pixels com **594 ms de ida e volta**. O pedido seguinte estava em andamento havia 141 ms quando o orçamento total venceu.

Isso identifica o desarme pelo software. O arquivo **não separava espera na fila do renderizador, cálculo e entrega do resultado**. Portanto, não permite afirmar que os 594 ms foram gastos calculando os efeitos, nem atribuir o atraso a CPU, GC, driver ou desenho. O último desenho curto também não comprova o custo do instante em que houve a pausa. [Resumo e hash do arquivo original](analise-falha1-v0.43.json).

## Falha encontrada no controle de idade

A versão 0.42 usava a hora de envio do pedido JavaScript como hora de criação do quadro. Se o pedido esperasse 594 ms na fila e então calculasse um quadro novo rapidamente, o controlador trataria esse RGB novo como antigo e o descartaria. O próximo pedido poderia ser desarmado pelo limite acumulado de 750 ms mesmo estando em andamento por apenas 141 ms.

O comportamento inverso precisa continuar protegido: um quadro que foi calculado antes e ficou retido por 594 ms na entrega está realmente velho e não pode ser transmitido.

## Mudança na versão 0.43

`outputFrames` passa a informar o início/fim do cálculo no relógio monotônico do renderizador e uma identificação da origem desse relógio. O host calcula um **limite superior conservador para a idade do RGB**, considerando a causalidade dos pedidos e a resolução do seu relógio. O início do cálculo é usado, para que um processamento demorado não apareça como quadro fresco só por ter terminado agora.

A calibração é renovada em respostas rápidas, reaproveitada por no máximo um segundo e tem margem para deriva. Não usa o horário civil do Windows nem mantém histórico crescente. Mudança de origem ou inconsistência de relógios provoca recalibração conservadora. Um primeiro pedido lento, sem referência, continua sendo avaliado pelo prazo total do pedido.

O limite de **250 ms para RGB antigo** continua existindo. A diferença é que a idade deixa de incluir indevidamente a espera anterior à geração. O worker USB recebe a hora conservadora de criação e ainda verifica o prazo antes de transmitir.

As seguintes proteções foram preservadas:

- Uma solicitação de pixels em andamento; nada de fila de frames atrasados.
- Apagamento temporário quando realmente faltam dados recentes.
- Desarme por ausência persistente de quadro válido, exigindo reativação manual.
- APAGAR TODAS, simulação, recarga, mudanças de montagem e callbacks antigos continuam impedindo retomada indevida.
- Falhas de ACK/USB continuam encerrando a conexão; watchdog do ESP32 preservado.
- Um quadro fresco que chega depois de um desarme já efetuado não rearma a saída sozinho.

Os logs agora distinguem `roundtrip_ms`, `javascript_ms`, `queue_lower_ms`, `age_bound_ms` e `reference_age_ms` dentro de `frame_timing`. A fila é um limite inferior estimado e a idade é um limite superior conservador, não medidas perfeitas dos relógios. A saúde também registra se a prévia estava visível, modo leve e qualidade.

## Reprodução e limites

O teste Qt/WebEngine usa janela visível, Apresentação leve desligada, Auto Show em camadas/build-up a 127 BPM, quatro saídas emuladas de 120 LEDs e a quarta copiando a primeira. Mantém captura sintética real em thread separada.

Espera injetada de **594 ms antes do cálculo**: o quadro novo é reconhecido como recente e o envio retoma sem rearmar manualmente. **Entrega atrasada de um RGB já gerado por 594 ms**: o quadro continua descartado. Uma pausa de **1.100 ms** ainda desarma; APAGAR durante a espera continua apagado depois da resposta. Não houve descarte de áudio ou erro JavaScript. [Relatório](resultado-frame-freshness-v0.43.0.json) · [Log](resultado-frame-freshness-v0.43.txt).

Esse ensaio reproduz uma causa possível de descarte indevido compatível com a sequência do arquivo. **Não determina retrospectivamente a origem da espera de 594 ms naquele computador.** Os novos campos permitem distinguir as situações se houver outra ocorrência. Também não garante emissão contínua durante uma parada real do motor: nesses casos o apagamento de segurança permanece.

Feche e reabra pelo **iniciar.cmd** para carregar a versão 0.43. Não precisa regravar o ESP32 nem alterar o projeto ou o mapeamento MIDI. [Validação](validacao.md).
