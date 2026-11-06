# Controladora MIDI — Traktor Kontrol X1 MK1

Disponível no BEATLIGHT **0.38.0**, pela página **Controladora MIDI**. O Auto Show continua funcionando sem controladora; o MIDI permite intervir na apresentação. A conexão não ativa automaticamente a saída USB das fitas.

Na **0.40**, há uma décima primeira função: **Marcar compasso 1 · trocas**. Ela usa a duração de compassos do Auto Show, sem alterar o sincronismo 1/8. Os perfis antigos mantêm suas dez associações; a nova fica livre para Learn. [Repertório único e referência](efeito-unico-e-compassos-v0.40.md).

## Preparar a X1 original

1. Conecte a X1 e confirme que o driver instalado a apresenta como dispositivo MIDI no Windows.
2. Na **X1 original / MK1**, pressione **SHIFT + HOTCUE** para alternar para o modo MIDI. [Instrução oficial](https://support.inmusicstore.com/en/support/solutions/articles/69000880031-native-instruments-switching-your-controller-to-midi-mode).
3. No **Controller Editor**, configure os botões usados pelo BEATLIGHT como **Gate**, para enviar pressão e soltura. Para o encoder de intensidade, configure CC absoluto ou um dos modos relativos abaixo. Os endereços dependem do seu template; o Learn dispensa um preset fixo.
4. Nos botões com retorno LED, escolha **LED On → For MIDI In**. Assim a iluminação acompanha mensagens recebidas do programa. O retorno local pelo próprio botão não informa o estado real do show. [Manual oficial, seção de estados dos LEDs](https://www.native-instruments.com/fileadmin/ni_media/downloads/manuals/Controller_Editor_Manual_English_2017_11.pdf).

O aplicativo usa MIDI nativo do Windows, sem pacote Python MIDI adicional. A X1 ainda depende de driver/Controller Editor compatíveis com seu Windows. O BEATLIGHT não instala nem modifica o template da controladora.

## Conectar e aprender

1. Reinicie o BEATLIGHT por **iniciar.cmd** e abra **Controladora MIDI**.
2. Clique **Atualizar portas**, escolha a entrada da X1 e a saída LED correspondente. Clique **Conectar MIDI**. **Sem retorno para LEDs** permite usar somente a entrada.
3. Selecione uma função na tabela e clique **Ativar Learn**.
4. Pressione o botão ou movimente o encoder. O primeiro endereço capturado aparece abaixo da tabela. Enquanto Learn estiver ativo, gestos MIDI não executam efeitos.
5. Clique **Encerrar Learn**. A associação fica em memória e já pode ser usada. Um endereço que já pertence a outra função é recusado, preservando a associação anterior.
6. Repita para outras funções. Clique **Salvar perfil** quando terminar. O asterisco indica alterações ainda não salvas.

Encerrar Learn e fechar o programa não substituem **Salvar perfil**. O arquivo **midi-controls.json**, cujo caminho aparece na tela, fica ao lado de preferences.json e pixel-studio.json. Na próxima abertura, as associações voltam; atualize as portas e conecte novamente. Não há conexão automática com hardware ao iniciar.

Para testar sem controladora, selecione a linha e use **Executar função selecionada**. Para intensidade, ajuste **Pico para teste**. As intervenções de estrutura também estão em **Pixel Studio → Comandos manuais**.

## Funções

| Função | Ação |
| --- | --- |
| Drop agora | Dispara imediatamente o drop existente por oito tempos. Outro toque encerra. Libera a estrutura manual anterior. |
| Breakdown manual | Mantém breakdown até novo toque no mesmo botão, outra estrutura ou seleção de modo de show. |
| Groove manual | Mantém groove com a mesma regra de liberação. |
| Build-up manual | Mantém tensão de build-up com a mesma regra de liberação. |
| Intensidade do pico | Ajusta de 0 a 100%, respeitando brilho, blackout e limites físicos. |
| Sincronizar beat 1/8 | Marca o primeiro tempo de um ciclo de oito tempos; precisa de grade recente. Não altera BPM nem fase do Traktor/Link. |
| Próxima combinação · no compasso | Agenda outra combinação no início do próximo compasso de quatro tempos. Repetir não adia. Durante um drop, aguarde o término. |
| Auto Show | Libera a estrutura manual e retoma o automático. |
| Orgânico | Libera a estrutura manual e seleciona o orgânico. |
| Contínuo | Libera a estrutura manual e alterna o contínuo fixo. Outro toque sai dele. |
| Marcar compasso 1 · trocas | Inicia a contagem até a próxima troca por compassos. Outro toque marca uma nova referência; exige grade recente ao vivo. |

A intervenção manual altera o contexto visual, sem fabricar kicks ou modificar a análise. Energia, baixo e densidade ainda vêm do áudio. Estruturas manuais, drop e agendamento são estados da sessão; o perfil persiste mapeamentos e opções MIDI.

O Auto Show permanece a base durante intervenções: seu LED pode ficar aceso junto de **Groove manual**. Pressionar **Auto Show** libera essa intervenção. Desconectar o MIDI mantém a apresentação e eventual estrutura manual; use os controles na tela para retomar o automático.

## Encoder da intensidade

Selecione **Intensidade do pico** e ajuste **Knob do pico** conforme o template:

| Modo no BEATLIGHT | Dados recebidos |
| --- | --- |
| Absoluto · 0 a 127 | CC 0 = 0%; CC 127 = 100%. |
| Relativo · +1 / 127 | 1 sobe um passo; 127 desce, complemento de dois. |
| Relativo · centro 64 | 65 sobe um passo; 63 desce. |
| Relativo · sinal + magnitude | 1 sobe um passo; 65 desce. |

Um passo relativo equivale a 1/127 da escala, limitada a 0–100%. Incrementos são processados em ordem; somente o último nível do lote segue para o motor. Se o sentido ou os saltos estiverem incorretos, confira o formato escolhido no Controller Editor. Notas também permitem intensidade pela velocidade de pressão, sem zerar na soltura.

## Retorno dos LEDs

1. Selecione uma função aprendida e clique **Usar endereço aprendido para o LED**. Aplica em memória retorno Note/CC com o mesmo canal e número.
2. Se seu template usar outro endereço, edite **Tipo**, **Canal**, **Número**, **Valor ligado** e **Valor desligado**, marque **Retorno habilitado** e clique **Aplicar retorno**.
3. Use **Testar LED · 1 segundo**. Depois do teste, volta o estado real.
4. Clique **Salvar perfil**.

Dois retornos não podem compartilhar endereço. Só mudanças são enviadas; os retornos mapeados são apagados ao desconectar/fechar normalmente.

- Drop: aceso enquanto ativo.
- Groove, Breakdown e Build-up: indicam a intervenção manual. A opção **LEDs de Groove / Breakdown / Build-up acompanham também a detecção automática** permite indicar a estrutura efetiva quando não há intervenção.
- Auto Show, Orgânico e Contínuo: indicam o modo atual.
- Próxima combinação: aceso enquanto agendada.
- Sincronizar beat 1/8: confirmação breve.
- Marcar compasso 1: aceso enquanto existe uma referência de trocas; apaga ao limpar a referência ou encerrar.
- Intensidade: valor proporcional, se o destino aceitar. Um LED binário pode mostrar somente ligado/desligado.

## Operação e diagnóstico

MIDI e as quatro fitas continuam com janela minimizada ou **Apresentação leve**. A tabela MIDI só é atualizada na sua página visível. Captura/grade recentes continuam necessárias ao vivo; MIDI respeita silêncio, blackout e saída física desativada.

Se a porta não aparecer, confira modo MIDI/driver e use **Atualizar portas**. Se estiver ocupada, confira outros programas ou mapeamentos MIDI do Traktor usando a mesma porta. Se um LED responde só à pressão, revise **For MIDI In**, saída escolhida e endereço. Falhas aparecem no status; o Auto Show continua independente da conexão MIDI.

Se a prévia deixar de responder, novas chamadas MIDI são interrompidas para não acumular solicitações. Use **Reabrir prévia**; a saída física exige ativação manual novamente. [Ensaios emulados e limites](validacao.md).
