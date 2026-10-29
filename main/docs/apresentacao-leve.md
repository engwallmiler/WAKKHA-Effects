# Operação e apresentação leve — Pixel Studio 0.26

## Simular o projeto que já está montado

O seletor no cabeçalho USB começa em **Simular projeto atual · sem USB**. Nesse modo a conexão serial e os quadros físicos ficam bloqueados. A geometria, as fitas, os grupos, os efeitos e as cores do projeto continuam disponíveis na prévia.

Clique **Simular meu projeto · sem USB** dentro do Pixel Studio para ativar a prévia. Se houver áudio recente, usa áudio/Link; caso contrário, escolhe **Demonstração · sem áudio**. O seletor da fonte continua acessível. A demonstração não analisa uma faixa real.

Se você estiver numa montagem temporária, o mesmo botão recupera o projeto original e inicia sua prévia. **Testar outra montagem** é a ação separada que cria quatro/seis/oito barras temporárias; **Voltar ao meu projeto** recupera a instalação original. Exporte para guardar uma montagem temporária.

Mudar da saída física para simulação apaga e desconecta a saída. Depois disso não há envio de quadros à COM. O comando de apagamento ainda é enviado durante o encerramento de uma saída ativa, antes de fechar a conexão.

## Usar a fita física

1. Selecione **Saída física · ESP32 USB** no cabeçalho.
2. Escolha a fita lógica, confira **Preparar 300 WS2812**, a COM e os limites.
3. Conecte e clique **Ativar saída física**. Conectar por si só não acende a fita.

**APAGAR SAÍDA** permanece acessível. Trocar para simulação, recarregar a prévia ou entrar numa montagem temporária deixa a saída desativada. Para retomar, escolha a operação física e ative explicitamente. O firmware 0.22 permanece compatível, sem regravação.

## Encontrar os controles

| Área | Uso |
|---|---|
| **Palco** | Prévia, fonte musical, ativação, blackout, sincronização, pico, drop e acesso rápido à fita selecionada. |
| **Efeitos e cores** | Automação, duração, fusão, camadas, picos, velocidade, paletas, RGB/RGBW e intensidade. |
| **Fitas e grupos** | Desenho, resolução, controles individuais e cartões de todas as conexões aplicadas. |
| **Biblioteca e drops** | Padrões manuais, timeline e parâmetros das sequências de drop. |

**Mostrar todos os controles** conserva a visão expandida anterior. **Editar fita** abre diretamente sua montagem e os controles individuais. Os painéis continuam recolhíveis.

As áreas de controles não desenham o palco em segundo plano, sem alterar a saída física. Em **Fitas e grupos**, os cartões verdes indicam conexões aplicadas; os campos são um rascunho até aplicar. [Cópias exatas e continuidade](conexoes-fitas.md).

## Deixar o Traktor em primeiro plano

Ative **Apresentação leve**, no cabeçalho nativo, para pausar o desenho do palco e os gráficos. Os controles de efeitos continuam disponíveis. Captura, DSP, Link e envio dos pixels permanecem ativos. A configuração USB é recolhida, mantendo ativação e apagamento visíveis.

Ao **minimizar a janela**, o aplicativo também suspende automaticamente desenho e atualizações gráficas. A música continua chegando ao motor; as chamadas de saída avançam o mesmo relógio dos efeitos. Ao restaurar, a imagem volta ao estado atual. Se Apresentação leve estiver ativa, continua pausada até desligar o botão.

O aplicativo não decide se a janela está encoberta por outra. Se quiser mantê-lo aberto atrás do Traktor, use **Apresentação leve**. Para acompanhar a prévia em outro monitor, deixe essa opção desligada e a janela restaurada.

## Espectro e outras telas

O espectro tem custo ao desenhar barras, gradientes e textos quando sua página está visível. Já tinha atualização condicionada à página; na 0.26 também exige janela restaurada e modo leve desligado. Oculto, minimizado ou no modo leve, não recebe essas atualizações.

A FFT continua necessária para energia por banda, transientes e características usadas pelos efeitos e detector. Fechar o gráfico não elimina esse DSP. A captura e a grade não são reduzidas para economizar desenho.

Audio Monitor, diagnósticos, Kick/Rhythm Monitor e palco anterior são atualizados somente quando usados. O worker PAR/moves fica suspenso quando suas páginas estão ocultas, a janela está minimizada ou Apresentação leve está ativa. Volta ao abrir Lighting Studio/Stage Preview com gráficos habilitados. Não existe saída DMX física ligada a esse worker.

O motor de pixels continua em Qt WebEngine. Uma falha nesse processo pode interromper os efeitos; o transporte conserva o apagamento e não reativa sozinho. O modo leve reduz trabalho gráfico, sem mover o motor para outro processo.

## Verificar nesta máquina

O [ensaio nativo](../scripts/validate_pixel_presentation.py) usa áudio sintético e ESP32 emulado, sem COM ou Link reais:

```powershell
.\.runtime\python312\python.exe -X utf8 scripts\validate_pixel_presentation.py --phase-seconds 8
```

Compara palco, controles, modo leve, minimização, espectro visível e palco PAR. Verifica movimento dos pixels, grupos, continuidade dos quadros emulados, zero descartes de áudio e ausência de atualizações gráficas ocultas. Registra CPU do processo principal e renderer. Os percentuais usam um núcleo lógico como 100%; não são o percentual total do Gerenciador de Tarefas. Resultados variam com máquina, configuração e carga.

[Resultados](validacao.md) · [Auditoria e ensaio prolongado](confiabilidade.md). Ensaios curtos não certificam seis horas reais.
