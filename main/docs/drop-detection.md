# Retorno do drop — versão 0.24

## Média dos picos do groove

A referência agora guarda duas médias em potência linear: o pico grave do kick e a potência do transiente descontando o som que já existia antes. Usa até 16 kicks aceitos e apara os extremos a partir de oito amostras. As médias ficam congeladas no breakdown/build, no contexto interno armado e no primeiro retorno; o candidato não altera a própria referência usada para julgá-lo.

Depois de passar por identidade e alinhamento, um kick com pelo menos 90% da potência média do transiente e 85% do pico médio pode provar diretamente a recuperação. Essa tolerância evita exigir igualdade numérica entre ataques. Assim, o retorno de força integral não precisa esperar a média dos graves da mixagem subir ou um crescimento de 7 dB sobre o breakdown. Não se espera outro kick para usar essa evidência.

O pico absoluto sozinho não basta: uma bassline alta com transiente fraco continua bloqueada. Os caminhos anteriores continuam disponíveis para retornos válidos de menor volume, com os filtros de potência, timbre, cadência e grade existentes. O diagnóstico do Stage Preview informa o pico médio, número de kicks e proporção do candidato. Essa razão é relativa ao groove, não uma medição elétrica nem KickEvent.intensity.

Há regressões para referência com acentos isolados, diferentes ganhos, tolerância de pico/transiente, graves altos sem ataque forte, roll fraco e congelamento da referência até o primeiro kick do drop. O comportamento continua heurístico; precisão e atraso em tracks reais precisam ser conferidos com os respectivos áudios.

## Novidade espectral e continuidade

A versão 0.23 expõe fluxo positivo normalizado e uma medida de novidade da distribuição de energia em 12 bandas, comparada com um fundo adaptativo de 0,9 s. Novidade não equivale a kick: apenas reforça um candidato que passou por identidade, potência e grade. O limiar reforçado para rolls acelerados continua ativo.

Após cerca de oito tempos sem kick forte, um contexto interno de retorno pode ser armado mesmo com baixo sustentado. Isso permite aproveitar o primeiro ataque real sem obrigar o painel a classificar a bassline como breakdown. A decisão acústica continua causal.

O estado de drop agora distingue **impact** e **confirmed**. O primeiro kick aprovado dispara o impacto imediatamente; três kicks acústicos únicos confirmam continuidade. Um impacto seguido de retirada real pode ser rejeitado, retornando ao contexto anterior. Uma lacuna de confirmações sobre graves sustentados permanece incerta e não encurta automaticamente os oito kicks, preservando o comportamento validado anteriormente.

A matriz completa do anexo, itens existentes, mudanças e limites está em [avaliacao-recomendacoes-drop-v0.23.md](avaliacao-recomendacoes-drop-v0.23.md). Não foi acrescentado um classificador de ML nem detecção de drop sem kick.

## Ajustes da versão 0.21

O detector agora distingue o instante de uma referência de groove do instante de um candidato fraco acelerado. A cadência dos candidatos brutos é acompanhada antes da filtragem pela grade: um roll fraco que começa ainda no groove não pode rebaixar continuamente a potência aprendida e impedir o armamento do retorno. Variações normais de volume com kicks no BPM original continuam permitindo adaptação da referência.

A confirmação espectral aceita um deslocamento de até **um bin** do FFT estrutural, exigindo similaridade de pelo menos 94% nesse caminho. Decaimento, ataque, excesso harmônico, potência e posição musical continuam obrigatórios. A correção da fase da grade não usa essa tolerância. Isso permite que o kick retorne com uma altura grave um pouco diferente sem aguardar outros ataques.

Um candidato recente fora da grade pode ocupar o intervalo mínimo do detector geral justamente antes do impacto. O caminho contextual pode recuperar um novo ataque alinhado, com pelo menos 60 ms de separação, desde que não seja duplicação de um candidato alinhado ou de uma recuperação recente. A identidade e a potência continuam sendo verificadas antes de contar o evento.

Novas regressões reproduzem um roll fraco que altera o aprendizado antes do build, kicks retornando com variações de altura, primeiro impacto bloqueado pelo refratário do detector geral e baixo lento/agudos que não devem virar drop. O caminho Pixel Studio também compensa a idade estimada das mensagens; a decisão acústica e o tempo de exibição são tratados separadamente.

Esses ajustes ampliam os casos cobertos, sem garantir detecção correta em todo arranjo. Não foram fornecidos arquivos de áudio das tracks problemáticas. O botão destacado **DROP AGORA** oferece intervenção manual imediata de oito tempos e não altera o estado musical detectado.

O detector continua causal e heurístico. A decisão rápida de entrada no drop foi separada da aprendizagem do timbre e da correção da grade. No breakdown/build-up aprendido e armado para retorno, procura-se reconhecer o primeiro kick forte com dados do próprio ataque. Não é necessário esperar o próximo kick nem o tempo 1 de uma frase.

## Duas janelas de análise

O groove aprende também a assinatura e o decaimento grave em uma janela curta, de 35–55 ms depois do timestamp do kick. O retorno compara a forma e o decaimento nessa mesma janela, descontando em potência o som que já tocava antes. Assim, um baixo sustentado deixa de encobrir automaticamente a cauda do kick.

A decisão rápida exige ao menos quatro referências, transiente semelhante ao perfil, queda de energia curta coerente, ataque suficiente e alinhamento musical. A potência ainda é comparada com o groove. Variações de cauda e um prato simultâneo podem passar sem exigir que todo o espectro da mixagem seja idêntico ao anterior. O desconto de harmônicos para pratos exige um ataque agudo pelo menos 8 dB acima do groove, é limitado à potência aguda medida e tem teto de 50% da potência grave. Harmônicos adicionais de bassline continuam sujeitos à rejeição.

Uma tentativa rápida incerta **permanece pendente** até a análise completa de 120 ms do mesmo ataque. O descritor rápido não alimenta o perfil aprendido e não pode autorizar uma correção da grade. Aquisição e correção de fase/BPM conservam a observação completa. As janelas indicam dados acústicos utilizados; captura, FFT, processamento e apresentação acrescentam latência.

## Recuperação de ataques e sincronização

Durante o retorno armado, um segundo caminho procura um aumento grave real quando o detector geral não publicou o primeiro evento. É necessário crescer pelo menos 3 dB acima do fundo e acrescentar potência equivalente a pelo menos 30% da referência, dentro da janela musical. Isso apenas cria um **candidato**: forma, decaimento e potência final ainda precisam validá-lo. Publicações tardias do detector geral são deduplicadas para não contar o primeiro kick duas vezes.

Com um provedor Link válido, conectado e selecionado, a fase externa valida a janela do ataque. A decisão deixa de depender de quatro novos kicks corrigindo uma grade acústica antiga. O primeiro ataque isolado não reposiciona essa grade. Sem Link, após ausência longa ou pausa recente, a previsão aceita uma tolerância limitada a 18% do tempo para o retorno forte; o contratempo permanece fora dessa janela. Uma mudança maior de fase exige a correção acústica consistente já existente.

O relógio, sozinho, nunca cria um kick. Depois da entrada, o drop continua contando oito confirmações acústicas, incluindo a primeira; a publicação duplicada desse impacto não avança o contador. A análise do transiente continua ativa durante esses oito kicks, com validação de timbre e potência, para o baixo sustentado não travar o contador. O novo caminho contextual é usado no retorno e no drop, sem relaxar globalmente o detector geral de kicks.

## Potência do groove e kicks do build-up

O perfil registra a potência grave do ataque, descontada a energia anterior. A média usa até 16 kicks aceitos em aprendizagem/groove, em escala **linear de potência**; com oito ou mais amostras, remove os dois extremos para limitar acentos isolados. Essa referência fica congelada durante breakdown e build-up.

A comparação não usa KickEvent.intensity: esse indicador é normalizado e pode atingir 100% mesmo num kick de amplitude menor. Um retorno precisa de pelo menos 70% da potência de referência. Se houver repetição acelerada, o limite sobe para 85%. Sem retorno de agudos comparável ao groove nem pausa recente, também se usa o limite de 85%. São limiares internos e não uma regra universal para todas as tracks.

A repetição acelerada exige dois intervalos recentes entre 30% e 68% do período original. Kicks fracos rejeitados continuam visíveis como candidatos acústicos, mas não reiniciam a ausência do kick forte, não reescrevem a grade e não alimentam a média aprendida. Um kick forte suficiente ainda pode iniciar o drop mesmo que o roll acelerado tenha acabado de terminar.

## Impacto, ausência e agudos

A recuperação dos graves considera o pico do próprio ataque e precisa superar a referência suavizada menos 4 dB. O crescimento de 7 dB sobre o mínimo do breakdown continua sendo uma das evidências de retorno. Quando o baixo já está forte durante toda a subida, um transiente separado do fundo e validado em forma, decaimento e potência também comprova a recuperação; não se exige que todo o baixo da mixagem suba outros 7 dB. Isso evita bloquear o primeiro kick ou esperar que uma média de 600 ms alcance o novo nível. O ataque rápido precisa acrescentar pelo menos 1,5 dB ao fundo; a comparação de potência com o groove continua obrigatória.

Cerca de oito tempos sem kick forte (limiar 7,5 períodos), ou uma pausa recente, reforçam o contexto e permitem a tolerância limitada de previsão. A tentativa rápida já está disponível nos retornos armados com perfil aprendido, sem aguardar oito tempos obrigatórios. Candidatos incertos conservam a janela de 120 ms para a análise completa do mesmo ataque. Não se promete luz no instante matematicamente exato do ataque.

Oito tempos são uma evidência de contexto, não uma obrigação nem uma previsão de que haverá drop. O relógio Link não cria kicks e não incrementa as oito confirmações reais do pós-drop.

## Pausa antes do drop

Uma queda de pelo menos 8 dB no RMS em relação ao trecho anterior, ou silêncio abaixo de −60 dBFS, mantida por pelo menos cerca de 60 ms, registra uma pausa recente no contexto de breakdown/build-up aprendido. A evidência expira em até um segundo depois do vale, dependendo do período.

Se o silêncio passa de 350 ms, o estado visual é **Silêncio** e as luzes ficam apagadas. Durante uma pausa curta desse contexto, a referência permanece disponível por até 2,5 períodos, limitada à faixa de 0,8–1,5 s. O retorno dentro desse prazo retoma a análise anterior, sem exigir quatro novos kicks. Silêncio longo descarta a referência; fonte/formato novos ou descontinuidade de captura continuam reiniciando os trackers.

Depois do silêncio, a melodia que reaparece junto com o kick não deve ser confundida automaticamente com excesso harmônico de bassline. O detector desconta somente o fundo harmônico aprendido no groove, limitado a 6% da potência do ataque grave. Essa compensação exige pausa recente; os limites de forma, decaimento, potência e grade permanecem. Ataques com harmônicos além desse fundo continuam bloqueados.

## Diagnóstico no palco

A linha de estrutura mostra a potência do último candidato de retorno como porcentagem da média do groove, retornos fracos bloqueados e presença de pausa recente. Depois de um drop, acrescenta o intervalo entre o timestamp do ataque e a decisão de análise e informa quando houve recuperação do ataque. Esse intervalo não mede a latência entre Traktor e luz apresentada. O motivo do estado informa quando um kick acelerado/fraco foi mantido no build. Passe o mouse sobre o texto para ver o conteúdo completo, sem alterar a geometria do palco.

StructureSnapshot.drop_evidence também publica referência/candidato em dB, razão de potência, tempos ausentes, prontidão, pausa, aceleração, retorno de agudos e motivo. confirmation_ms, fast_confirmed e rescued_attack descrevem a última entrada no drop. Esses dados acompanham a exportação de diagnóstico JSON.

A análise não identifica literalmente um upfilter nem conhece a estrutura futura da faixa. Ela precisa aprender o perfil de um groove antes de autorizar drops. Mudanças grandes de timbre, volume ou fase e baixos muito semelhantes a kicks ainda podem exigir evidência adicional ou gerar erros. Os testes incluem variações de cauda, frequência, volume, baixo contínuo, prato no primeiro impacto, falha do detector geral e desvio de fase, além das rejeições anteriores. Não há arquivo de áudio real das tracks citadas para calibração nesta rodada.
