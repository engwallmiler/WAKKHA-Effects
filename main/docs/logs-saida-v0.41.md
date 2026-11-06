# Saída física, logs e contador de batidas — 0.41

## Investigação do apagamento

O botão de saída ficou desativado e bastou ativá-lo novamente, sem reconectar o ESP32. Esse comportamento é compatível com um desarme pelo painel, mantendo a porta COM aberta. Uma falha de confirmação USB encerra a conexão e exige reconectar.

O arquivo antigo `logs/beatlight.jsonl` continha eventos de início/parada da captura, sem os motivos de desarme USB. Como o horário do episódio não foi identificado, **não é possível afirmar sua causa exata**.

Foi encontrada e reproduzida uma condição que pode explicar esse comportamento: antes, uma única resposta JavaScript com mais de 250 ms desarmava definitivamente a saída. Uma pausa momentânea da interface também podia tornar um quadro atrasado e provocar esse desarme. Além disso, no Windows, os diálogos nativos de arquivos interrompem os QTimers enquanto estão abertos, conforme a [documentação do Qt](https://doc.qt.io/qt-6/qfiledialog.html). O aplicativo agora usa os diálogos do próprio Qt, que permitem continuar esses temporizadores. Isso não prova que um diálogo causou o episódio relatado.

## Comportamento de segurança

| Situação | Resultado |
|---|---|
| Quadro com mais de 250 ms | Descartado; não é transmitido depois. |
| Atraso breve da prévia ou interface | Apagamento temporário; tenta receber um quadro novo, mantendo a saída armada. |
| Quadro novo chega dentro do orçamento de recuperação | Envio retoma automaticamente. O aviso e a recuperação ficam registrados. |
| 750 ms sem um quadro válido novo | Desarme; exige ativação manual após a prévia responder. |
| Falha USB, ACK ausente ou comando rejeitado | Conexão encerrada, saída desarmada; exige reconexão manual. |
| APAGAR TODAS, simulação, recarga ou mudança de montagem | Continua respeitando o desligamento solicitado; não rearma automaticamente. |
| Silêncio, captura parada/atrasada ou blackout lógico | O motor produz zero. O log distingue esse bloqueio de um desarme físico. |

O orçamento de 750 ms é contado desde o último quadro válido, ou desde a ativação inicial; respostas continuamente atrasadas não o renovam. Há no máximo um pedido de quadro em andamento, mesmo após um desarme. Enquanto a resposta antiga não voltar, a ativação fica bloqueada; se persistir, use **Reabrir prévia**. Uma resposta de uma prévia anterior não libera nem transmite o pedido da nova.

O worker USB conserva seu limite de 250 ms para apagar por falta de dados recentes. O watchdog de 750 ms do ESP32 permanece independente: ele não depende de a interface continuar funcionando. Os limites são prazos de software sujeitos ao escalonamento do computador; não prometem temporização elétrica exata.

## Usar os logs

1. No topo do Pixel Studio, abra **Logs da saída**. A janela é separada e não interrompe o show.
2. Use **Avisos e erros** ou procure `frame_timeout`, `COM5`, `transport_error` etc.
3. Selecione uma linha para ver seu contexto: conexão, firmware/protocolo, saídas, quadros, atrasos, confirmação USB e estado do motor.
4. Use **Exportar diagnóstico**. O JSON inclui os eventos recentes, o último aviso/erro e até 60 amostras recentes de saúde. **Abrir pasta de logs** mostra os arquivos persistentes.

Os horários da tabela usam **dia/mês/ano e 24 horas, com milissegundos**, convertidos ao fuso local configurado no Windows. O arquivo guarda o horário local ISO com deslocamento e uma referência UTC para correlação. Não fixa o fuso em Brasília; se o relógio/fuso do Windows estiver incorreto, o registro seguirá essa configuração. O log geral de áudio e os eventos da interface também passaram a usar o horário local. Registros UTC antigos são convertidos ao serem apresentados.

Foi verificado neste ambiente que `TZ=GMT0` forçava o relógio local do Python a UTC apesar de o Windows estar configurado em UTC−3. A conversão usa agora [SystemTimeToTzSpecificLocalTimeEx](https://learn.microsoft.com/en-us/windows/win32/api/timezoneapi/nf-timezoneapi-systemtimetotzspecificlocaltimeex), consultando o fuso ativo do Windows e suas regras históricas, sem alterar o ambiente do processo. Testes conferem mudança de dia e datas com/sem o antigo horário de verão, comparando com o fuso explícito do Qt.

O campo **Último aviso** permanece depois de reativar a saída e pode ser recuperado dos arquivos ao reiniciar. Um novo aviso/erro pode substituí-lo; os anteriores continuam na lista até os limites de retenção. O botão de pausar congela somente a lista, sem suspender a coleta.

Eventos úteis:

| Código | Interpretação |
|---|---|
| `output.activated`, `output.manual_stop` | Ativação ou apagamento pelo operador. |
| `output.frame_gap`, `output.recovered` | Atraso breve e retomada com quadro novo. |
| `output.frame_timeout` | Desarme por 750 ms sem quadro novo. |
| `usb.producer_gap` | Worker apagou temporariamente por falta de quadros recentes. |
| `usb.transport_error` | Erro do driver, escrita, ACK ou validação do dispositivo; inclui comando, sequência e exceção. |
| `output.invalid_frame` | Quadro ou montagem incompatível; mensagem original preservada. |
| `output.gate` | Motor emitindo, em silêncio, sem áudio recente, em blackout, pausado ou desativado. |
| `output.preview_reload`, `output.project_mapping_changed` | Recarga ou alteração de montagem que exige nova ativação/reconexão. |

As amostras mostram o tempo entre ticks da interface, idade de pedidos, idade dos dados musicais, último tempo de renderização, BPM/estrutura e estatísticas USB. O uptime informado pelo firmware vem em milissegundos de 32 bits e pode voltar a zero após reinício ou rollover; sozinho ele não comprova uma falha elétrica. O protocolo atual não informa diretamente a causa de um reset nem eventos do watchdog. Logs do computador não detectam com certeza falta de alimentação ou falha elétrica na fita.

## Custo e retenção

- Até **1.000 eventos** em memória, **60 amostras** de saúde a 1 Hz durante o envio e **256 escritas** pendentes.
- Um arquivo `pixel-output.jsonl` de até aproximadamente **2 MB**, mais **três cópias** rotativas. O log geral `beatlight.jsonl` mantém sua própria rotação de aproximadamente 8 MB.
- Gravação, leitura do histórico e exportação em threads auxiliares. Disco lento ou indisponível não bloqueia o envio; a janela mostra falhas de gravação e contagem de escritas descartadas por saturação.
- A tabela atualiza no máximo duas vezes por segundo enquanto visível, somente quando os eventos mudam. Ao fechar, seu temporizador para; a coleta continua.
- Não grava áudio bruto nem os quadros RGB. Não registra cada quadro/ACK em disco. O pacote de diagnóstico por quadro contém somente alguns descritores escalares e não reamostra os pixels.

Os eventos persistem entre sessões; as amostras de saúde são um histórico recente em memória e ficam no arquivo exportado, sem gravação contínua de telemetria em disco.

## O contador pode estourar?

A **fase** representa a posição dentro de uma batida e permanece entre 0 e 1, exibida como 0–100%. O número crescente era o **índice acumulado da grade**. Em seis horas a 128 BPM, ele avança apenas **46.080 tempos**.

No Python esse índice é um inteiro de precisão arbitrária. No JavaScript usa `Number`, que representa inteiros exatos até 2⁵³ − 1; algumas horas estão muito longe desse limite. Não há uma fila de batidas crescendo junto com esse número. Outros contadores, como sequência USB, uptime do ESP32 e identificação de entrega Qt, têm limites próprios e tratamento separado.

O mostrador **Fase da batida** agora exibe um ciclo relativo de **1 a 8** e a fase em porcentagem. O tooltip conserva a contagem acumulada. A grade interna não foi zerada, preservando referências de até 128 compassos, sincronismo, cores e efeitos. Esse ciclo visual não afirma a posição original do compasso da track.

## Validação e atualização

Os testes nativos usam Qt/WebEngine real e ESP32 emulado: pausas de 400 ms na prévia e 350 ms na interface retomam sem rearmar; uma pausa de 1.100 ms desarma; um ACK retido encerra a USB e registra o comando. Os diálogos de arquivo e a janela de logs mantêm os quadros em andamento. Há testes de disco indisponível, fila saturada, rotação, recarga, callbacks antigos e contadores grandes. [Resultado específico](resultado-output-diagnostics-v0.41.0.json) · [Validação da entrega](validacao.md).

Feche normalmente e abra novamente por **iniciar.cmd** para carregar a versão 0.41. **Não precisa gravar o ESP32 novamente**: firmware e formato do protocolo foram preservados. Esta entrega não inclui ensaio de seis horas reais nem reprodução do episódio original com hardware conectado.
