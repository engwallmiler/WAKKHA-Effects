# Drop por BPM e referência reversível — 0.42

## Marcar e desmarcar compasso 1

O primeiro clique em **Marcar compasso 1** inicia a referência das trocas de efeito. O botão fica destacado e passa a mostrar **Desmarcar compasso 1**. Outro clique desativa a referência, remove o destaque/contador e recalcula o agendamento normal, preservando o padrão atual. Para marcar uma nova origem, desmarque e marque novamente no momento desejado.

Esse comando não altera BPM, posição da grade, Sincronizar 1/8, Sincronizar pico, cores nem duração de um drop em andamento. Para criar uma referência ao vivo, é necessária uma grade recente. Para **desmarcar**, não é necessário esperar a grade voltar.

No MIDI Learn, a função se chama **Compasso 1 · marcar/desmarcar**. A associação existente foi preservada: a mesma tecla alterna os estados, inclusive com o aplicativo minimizado. O retorno LED acende ao marcar e apaga ao desmarcar. Não precisa refazer o mapeamento ou salvar o perfil novamente só por esta atualização.

## Oito tempos de drop sem esperar oito confirmações

O drop automático continua entrando pela decisão musical existente. Após entrar, sua duração passa a ser **oito tempos estimados pelo BPM**, equivalentes a dois compassos de 4/4. Não espera mais oito kicks confirmados pelo detector.

| BPM | Duração de oito tempos |
|---|---|
| 120 | 4,00 s |
| 128 | 3,75 s |
| 150 | 3,20 s |

O primeiro impacto é o início do tempo 1; o tempo 8 começa após sete intervalos e termina após oito intervalos. A regra vale para o efeito visual, sua evolução e o retorno ao Auto Show. Pulsos e entrada progressiva das camadas do drop também seguem esse avanço, mesmo com a confirmação de kicks parada. **DROP AGORA** continua imediato, dura oito tempos e pode ser cancelado por outro toque.

A indicação do Pixel Studio mostra a posição em oito tempos, o tempo restante e a contagem acústica real separada. Por exemplo, o efeito pode chegar ao tempo estimado 7/8 enquanto o detector só confirmou dois kicks. Isso não cria eventos acústicos fictícios nem altera o BPM para fazer a contagem fechar.

No Pixel Studio, a duração acompanha o relógio selecionado: **Ableton Link ou grade acústica**. Se a grade ficar temporariamente indisponível, mas o áudio ainda for recente, usa o último BPM conhecido para terminar o drop. Correções/rebases da grade e Sincronizar 1/8 preservam o tempo restante. Sem áudio recente, as proteções de silêncio/atraso continuam apagando a emissão.

No analisador de estrutura, o período confiável no momento do impacto fixa um prazo de oito tempos. Pequenas mudanças posteriores no estimador não alongam esse prazo. O contador de kicks confirmados permanece diagnóstico. Uma retirada real dos graves ou uma nova estrutura musical pode encerrar o drop antes; voltar a groove pelo detector não encurta sozinho os oito tempos da apresentação.

O pacote musical informa a idade do impacto para o simulador descontar o tempo já transcorrido. Um pacote atrasado não ganha oito tempos adicionais; um drop já expirado não começa de novo. O mesmo identificador não reinicia o efeito depois de terminado, e um novo identificador pode iniciar o próximo drop.

## Validação e atualização

Os testes cobrem BPMs diferentes, ausência/duplicação de confirmações, grade temporariamente indisponível, pacotes atrasados, correção da grade e cancelamento por nova estrutura. A comparação visual verifica que a progressão do drop é a mesma com uma ou várias confirmações. O ensaio Qt/MIDI com quatro saídas emuladas confere o drop automático com contador parado em 1, retorno do LED ao encerrar e marcação/desmarcação minimizada.

Os algoritmos de identificação de kick e entrada do drop foram preservados; mudou o critério de **duração**. Há apenas cálculos escalares nos caminhos existentes, sem novas threads, FFTs ou históricos. Firmware e transporte USB permanecem compatíveis.

Reabra o aplicativo pelo **iniciar.cmd**. Não precisa regravar o ESP32. [Validação](validacao.md) · [MIDI](midi-x1-mk1.md) · [Logs da saída](logs-saida-v0.41.md).
