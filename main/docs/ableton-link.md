# Ableton Link com o Traktor — BEATLIGHT 0.17

O módulo Link já está instalado no Python portátil deste computador. Feche a versão anterior e abra **iniciar.cmd** para ver **Ableton Link** no menu lateral. Ele funciona separado da captura de áudio e pode ser monitorado mesmo sem iniciar WASAPI.

## Configuração no Traktor

1. Confirme que a faixa foi analisada e que o **beatgrid está correto**. Um grid errado no Traktor também produzirá luzes fora do tempo.
2. Nas versões atuais, abra **Preferences → External Sync → External Clock Source** e selecione **LINK**, para exibir o botão no Master Control. Em versões anteriores, confira a exibição da **Global Section** em Preferences → Global Settings.
3. Em **Preferences → Transport → Sync Mode**, escolha **BeatSync**. TempoSync iguala a velocidade, mas pode deixar a fase do deck desalinhada.
4. Ative **LINK** no painel global/Master Clock do Traktor. Ative **SYNC** no deck e reproduza a faixa.
5. Confira o BPM global: com Link ativo, o **Master Clock** é a referência dos decks. A sessão usa inicialmente o tempo do primeiro participante; alterações posteriores do tempo são compartilhadas. Por isso, ative o Link no Traktor primeiro e confira o BPM antes de começar o show. Se o BEATLIGHT for o primeiro participante, sua sessão local começa em 120 BPM e um Traktor que entrar depois poderá adotar esse tempo.

Os nomes e a posição dos controles dependem da versão do Traktor. Consulte o [manual da Native Instruments, seção sincronização com Ableton Link](https://docs.native-instruments.com/ni-tech-manuals/traktor-pro-manual/en/advanced-operation-of-traktor) e o [guia de conexão e BeatSync da NI](https://support.native-instruments.com/support/solutions/articles/69000879473-how-to-sync-traktor-to-other-applications-via-ableton-link).

## Configuração no BEATLIGHT

1. Abra **Ableton Link** e clique em **Ativar Ableton Link**.
2. Aguarde **CONECTADO** e pelo menos **1 participante**. O contador representa outros aplicativos da sessão; o protocolo não identifica qual é o Traktor.
3. Marque **Usar Link como relógio da grade e dos efeitos**. A métrica **RELÓGIO DOS EFEITOS** deve indicar **LINK**. Desmarcado, o Link fica apenas em monitoramento e os efeitos seguem a análise por áudio.
4. No **Audio Monitor**, selecione **WASAPI Loopback**, escolha a saída usada pelo Traktor e clique **Iniciar captura**. Mantenha a configuração de áudio que já funcionou nos testes anteriores.
5. Em **Stage Preview**, ative o motor e deixe **Show de 8 · LIGADO**. Agora a grade e os padrões usam BPM/fase Link, inclusive durante trechos sem kick. **Rhythm Monitor** mostra o selo ABLETON LINK; o histórico abaixo continua sendo diagnóstico do detector acústico.
6. Clique **Sincronizar 1/8** no primeiro tempo desejado de um grupo de **oito tempos**. Isso marca o início do ciclo visual; não altera o grid, BPM, transporte ou posição da track no Traktor. A fase compartilhada não reconhece sozinha o começo musical de uma frase de oito.
7. Se o pulso visual parecer adiantado em relação ao som, aumente **Compensação visual**. Se parecer atrasado, use um valor negativo. Comece em **0 ms** e ajuste em passos pequenos. A faixa é −250 a +250 ms e o ajuste pertence somente ao BEATLIGHT.

A preferência de relógio e a compensação são salvas ao fechar ou salvar os ajustes gerais. **Ativar Link** é um estado desta sessão: a conexão começa desativada a cada abertura. Se houver zero participantes, falha do módulo ou mais de 500 ms sem amostra válida, a aplicação volta à referência por áudio. A mudança de fonte limpa o alinhamento visual manual; marque novamente Sincronizar 1/8 depois de uma reconexão, correção grande ou ajuste de compensação.

## O que esperar

Link compartilha **tempo, batida e fase**, não áudio, análise de instrumentos, nome da música ou posição absoluta da faixa. Não exige Ableton Live instalado. A linha de tempo Link pode avançar com os decks parados; por isso, o BEATLIGHT continua exigindo captura e áudio recente para a automação, e respeita silêncio, motor desativado e blackout. O retorno de um kick e as oito confirmações do pós-drop continuam acústicos: pulsos previstos nunca viram kicks. Veja os [conceitos oficiais do Ableton Link](https://help.ableton.com/hc/en-us/articles/209776125-Link-features-and-functions-FAQ).

A implementação lê a sessão pelo adaptador nativo aalink 0.2.3/SDK Ableton Link. Não chama comandos para mudar tempo, beat ou play/stop. O quantum local de oito tempos organiza o ciclo visual, sem afirmar que é a frase real da música. O perfil/timbre do kick e a grade acústica usados na auditoria permanecem independentes da grade externa exibida no palco.

## Se não conectar ou se ficar fora de fase

- **Sem participantes:** confirme LINK ativo nos dois aplicativos. Eles devem estar no mesmo computador ou na mesma rede local. Prefira Ethernet. Redes Wi-Fi com isolamento de clientes e algumas VPNs impedem descoberta entre participantes.
- **Firewall:** confira a permissão para o executável Python usado por iniciar.cmd na sua rede privada. Nesta instalação, é normalmente **.runtime/python312/python.exe**. Não desative o firewall. O aplicativo não muda regras de rede automaticamente.
- **Mesmo BPM, kicks fora da grade:** use BeatSync e confira o beatgrid do deck. A NI também orienta desligar e ligar novamente SYNC para realinhar decks que usavam TempoSync. Sincronizar 1/8 corrige somente o início do ciclo das luzes; não corrige o beatgrid da faixa.
- **Deslocamento visual constante:** ajuste a compensação local. Diferenças na cadeia de áudio/captura podem deslocar som e luz mesmo quando os aplicativos compartilham a mesma fase.
- **Módulo ausente em outro ambiente:** feche o BEATLIGHT e execute **instalar-link.cmd**. Ele usa o mesmo critério de seleção do iniciar.cmd: ambiente Python 3.12 completo, ou Python portátil. Precisa de internet para instalar aalink 0.2.3. Em caso de erro de DLL, confira o Microsoft Visual C++ Redistributable 2015–2022 x64.

As recomendações de rede e alinhamento de decks vêm do [suporte da Native Instruments](https://support.native-instruments.com/support/solutions/articles/69000879473-how-to-sync-traktor-to-other-applications-via-ableton-link). O wrapper utilizado está documentado no [projeto aalink](https://github.com/artfwo/aalink).

## Diagnóstico independente, opcional

Com LINK já ativado no Traktor, abra PowerShell na pasta main e execute:

~~~powershell
& '.\.runtime\python312\python.exe' -X utf8 -m beatlight.sync --seconds 15
~~~

O comando ingressa temporariamente na sessão Link, imprime estado, BPM, posição em tempos e participantes e sai após 15 s. Não inicia captura nem motor de luz. Código 0 significa que encontrou uma sessão com participante; 1 significa que não houve conexão válida no período; 2 indica erro do módulo. Encerre esse diagnóstico antes de testar a contagem de participantes na interface.

Para desenvolvimento, **scripts/validate_link.py** testa dois participantes nativos locais, verifica a fase compartilhada e encerra ambos. Ele pode aparecer como dois participantes temporários em uma sessão já existente e não escreve BPM ou transporte. Esse ensaio foi aprovado nesta máquina; a avaliação com tracks reais no Traktor continua sendo um teste operacional separado.
