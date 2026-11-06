# Buffers, filas e sessões prolongadas — 0.40.0

A revisão mantém o processamento musical e o protocolo físico. O novo modo de efeito único reduz o número de padrões calculados e evita capturas de misturas durante transições interrompidas. Não há um histórico de quadros proporcional ao tempo de apresentação.

## Limites conferidos

| Área | Limite e comportamento |
| --- | --- |
| Captura de áudio | RecentBlockQueue usa a capacidade configurada, com oito blocos como padrão. Ao encher, descarta o bloco mais antigo. |
| Música → WebEngine | Um pacote em trânsito e somente o pacote pendente mais recente. A confirmação precisa corresponder ao identificador em trânsito. |
| MIDI de entrada | Até 512 mensagens curtas. Clock/Active Sensing são filtrados antes da fila. Excesso é detectado e o lote é descartado para evitar gestos antigos. |
| Comandos MIDI → efeitos | Até 64 pendentes, intensidade coalescida e uma chamada JavaScript ativa. Sem resposta em 500 ms, novos comandos são bloqueados até recuperar a prévia. |
| Retorno LED MIDI | Somente o último estado de até onze endereços; transmite mudanças, sem uma fila crescente de estados. |
| Pixels → USB | Um quadro pendente, substituído pelo mais recente, e um envio em andamento. As quatro saídas compartilham o quadro. |
| Recepção serial | Leituras de até 4.096 bytes e payload validado de até 3.600 bytes. O caminho normal trabalha com menos de aproximadamente 8 KB de dados de parser, inclusive a leitura seguinte. |
| Histórico USB | Até 31 tempos de confirmação. Quadros vencidos são descartados; falha do renderer desarma a saída. |
| Geometria | Até 32 linhas e 8.192 pixels de projeto. Cada saída física aceita até 300 LEDs; quatro saídas somam até 1.200. |
| Buffers de efeitos | Canais físicos, sinais e texturas são reutilizados por identidade/resolução. Mover linhas, marcar compassos e trocar efeitos não altera suas dimensões. |
| Efeito único | Um descritor estável ou dois durante a fusão. Zero buffers de snapshot de misturas. |
| Camadas | Snapshots são arrays planos dos pixels existentes, sem uma cadeia recursiva de misturas. Os testes conservam a verificação dos limites anteriores. |
| Seleção de efeitos | Histórico de doze composições, duas variantes recentes de drop e sacos de seleção limitados ao catálogo/contextos. |
| Repertório personalizado | Até 33 regras, uma por efeito conhecido, com booleano de ativação e duração validada entre as opções até 128 compassos. |
| Temporizadores | Um agendamento de prévia e um salvamento de projeto debounced; não se cria um timer por compasso, efeito ou LED. |
| Salvamento | Uma gravação ativa e somente a última edição pendente. Projeto limitado a 500 KB; perfil MIDI a 32 KB. Escrita atômica fora da interface. |
| Diagnósticos | Eventos/erros de interface usam históricos limitados; o log em disco usa rotação de 2 MB com três cópias anteriores. |

## Correções desta rodada

**Identificador de entrega:** o contador Python agora retorna a 1 antes de ultrapassar o máximo inteiro assinado de 32 bits aceito pelo slot Qt que confirma os pacotes musicais. Confirmações antigas continuam sendo ignoradas. O limite é forçado nos testes; não seria alcançado em poucas horas na taxa normal de envio.

**Transições do modo único:** quando outra troca chega antes do fim da fusão, escolhe um dos descritores anteriores como origem e substitui o destino. Não amostra o palco para guardar uma mistura, e não aumenta o número de efeitos em cadeia.

**Agendamento:** os intervalos longos são números, não listas de batidas ou de quadros. Após um salto de relógio, o cálculo passa diretamente ao ciclo futuro; não cria uma fila para reproduzir trocas perdidas. A chegada ligeiramente atrasada de um pacote não desloca os próximos prazos da referência marcada.

**Modo de demonstração:** agora respeita Manter padrão/Somente novos elementos, evitando trocas por tempo quando a interface dizia para manter o efeito.

**Paletas e sincronismo:** a origem da evolução cromática acompanha o reajuste do relógio. Paletas compartilhadas por dois descritores são deslocadas uma única vez, evitando congelar ou deslocar duas vezes sua progressão após Sincronizar 1/8.

## Validação e limites

Os testes verificam 48 horas de relógio musical acelerado, com trocas, mudanças de estrutura, marcações e correções de relógio: histórias limitadas, buffers estáveis e até dois padrões no modo único, sem snapshots. Há também ensaio nativo com áudio sintético, serial emulada, gravações artificialmente lentas, congelamento temporário do renderer, descarte de quadros vencidos e reabertura da prévia. [Resultados desta versão](validacao.md).

Tempo musical acelerado não equivale a executar o programa por seis horas reais. Para repetir um ensaio real de seis horas, sem hardware físico:

```powershell
.\.runtime\python312\python.exe -X utf8 scripts\validate_pixel_endurance.py --single --seconds 21600 --music-hours 6
```

O teste abre uma instância isolada com captura sintética e ESP32 emulado; não usa a configuração da apresentação. O comportamento dos drivers reais, do Traktor, do cabo USB e da alimentação das fitas ainda depende de validação no conjunto físico.
