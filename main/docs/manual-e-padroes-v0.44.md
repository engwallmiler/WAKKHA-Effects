# Manual no palco e seis padrões novos — 0.44

## Operar sem trocas automáticas de desenho

Clique **MANUAL** na barra principal, junto de Auto Show e Orgânico. O botão fica verde e aparece uma linha de navegação logo abaixo da prévia dos LEDs:

**◀ Anterior · seletor de padrão · Próximo ▶**

O seletor oferece **39 padrões**, com nome e número. Anterior/Próximo percorrem a lista; depois do último volta ao primeiro. A entrada no Manual assume imediatamente o desenho escolhido, sem carregar a combinação de camadas anterior. As próximas escolhas usam a fusão musical configurada, limitada a dois tempos, ou corte se a fusão estiver em zero. Uma sequência rápida de cliques não cria snapshots ou uma cadeia crescente de misturas.

O padrão permanece selecionado entre frases, compassos e mudanças de groove/breakdown/build-up/drop detectadas. A música continua modulando movimento, energia e cores conforme os controles, sem substituir o desenho escolhido. O Kick Pulse manual pode pulsar pela grade BPM mesmo quando faltam confirmações acústicas.

Os botões do catálogo na Biblioteca também selecionam o desenho no modo Manual. As setas esquerda/direita funcionam quando o foco está fora dos campos e botões; **N** avança e **P** retorna.

## Sair do Manual

Clique em **Auto Show**, **Orgânico**, **Contínuo**, **Drop**, **Groove**, **Breakdown** ou **Build-up**. O Manual desativa, a navegação recolhe e o modo escolhido passa a controlar os efeitos. Outro clique no próprio botão Manual retorna ao Auto Show.

O Drop disparado enquanto o Manual está ativo continua imediato por oito tempos e retorna ao Auto Show ao terminar. Um drop detectado pelo áudio não toma sozinho o controle do Manual.

Os comandos já mapeados na X1 para os outros modos também saem do Manual. Os perfis MIDI existentes foram preservados; nesta rodada, Manual/Anterior/Próximo são controles da interface e não novas funções de Learn. O comando MIDI existente de próxima combinação, se usado no Manual, agenda o próximo padrão para o início do próximo compasso.

Brilho, velocidade, paleta, pico, Sincronizar 1/8 e referência de compassos são ajustes: não encerram o Manual.

## Efeitos individuais, geometria e segurança

No Manual, o padrão global escolhido tem prioridade sobre os efeitos individuais das fitas. A intensidade usa uma base modulada pela energia, para uma resposta individual configurada como kick não esconder a seleção por falta de confirmações. Isso é temporário: os controles individuais permanecem salvos e voltam a valer ao sair do Manual.

Continuam valendo brilho mestre/por fita, fitas desabilitadas, sentido, velocidade/fase individuais, continuidade, cópias exatas e paletas próprias. Silêncio, áudio antigo, blackout, simulação sem USB e apagamento manual conservam suas proteções. Escolher um padrão não conecta nem arma uma saída física.

O projeto guarda o último padrão manual e se esse modo estava ativo. Ao voltar depois de outro modo, o botão Manual recupera a última escolha. Projetos antigos continuam abrindo com seu comportamento anterior; não passam automaticamente a substituir efeitos individuais. Em um projeto antigo com desenho fixo, a primeira ativação do Manual usa esse mesmo desenho.

## Novos padrões

| Padrão | Desenho |
|---|---|
| **Ondas estacionárias** | Nós simétricos que se abrem e se fecham em um movimento hipnótico. |
| **Portais** | Anéis espelhados que avançam do centro às extremidades. |
| **Zíper** | Segmentos alternados abrem e fecham a fita em ciclos rítmicos. |
| **Diamantes** | Uma malha diagonal de pontos e contornos luminosos. |
| **Fitas prismáticas** | Faixas coloridas em movimento, com espaços escuros entre os núcleos. |
| **Seda luminosa** | Todos os LEDs acesos, com ondas suaves de cor e brilho. |

São funções periódicas de espaço/tempo, com cálculo limitado por pixel. Não usam partículas com vida crescente, histórico de posições ou sorteio a cada quadro. Trabalham na mesma amostragem da prévia e dos LEDs físicos, preservando cópias e sentidos invertidos.

Os novos desenhos também ficam disponíveis no repertório do Auto Show de **Efeito único** e nas combinações variadas. Um repertório personalizado antigo mantém suas escolhas: os seis desenhos novos ficam desmarcados até serem habilitados. Restaurar o repertório oferece o catálogo completo. As famílias hipnóticas em camadas existentes foram conservadas.

## Preservação da versão estável

O operador relatou duas horas sem interrupções com a 0.43. Por isso, esta alteração foi concentrada nos controles, validação do projeto e desenhos. A comparação confirma **93 módulos Python preservados**, incluindo captura, DSP, estrutura, Link, MIDI, USB e cálculo de idade dos quadros. Em `ui/window.py`, mudou somente o texto da versão. Os caminhos JavaScript de emissão, amostragem física, carimbo temporal e política de renderização também foram comparados. [Registro](resultado-core-preservado-v0.44.json).

Não foi alterado o firmware, formato serial, watchdog, filas ou prazos de segurança. A validação inclui interface compacta, navegação rápida, parâmetros antigos, cópias invertidas e quatro saídas emuladas. Isso preserva os caminhos já validados, sem substituir um novo ensaio prolongado com o conjunto físico. [Resultados](validacao.md).

Feche completamente o aplicativo e reabra pelo **iniciar.cmd** para carregar a 0.44. Não precisa regravar o ESP32 ou refazer os perfis MIDI.
