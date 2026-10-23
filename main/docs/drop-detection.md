# Retorno do drop — versão 0.18

O detector continua causal e heurístico. Um ataque precisa passar pelo perfil de kick e pela grade acústica. A nova camada compara sua potência com o groove aprendido, preserva o contexto em pausas curtas e usa o pico do ataque para reconhecer o impacto no primeiro kick forte elegível.

## Potência do groove e kicks do build-up

O perfil registra a potência grave do ataque, descontada a energia anterior. A média usa até 16 kicks aceitos em aprendizagem/groove, em escala **linear de potência**; com oito ou mais amostras, remove os dois extremos para limitar acentos isolados. Essa referência fica congelada durante breakdown e build-up.

A comparação não usa KickEvent.intensity: esse indicador é normalizado e pode atingir 100% mesmo num kick de amplitude menor. Um retorno precisa de pelo menos 70% da potência de referência. Se houver repetição acelerada, o limite sobe para 85%. Sem retorno de agudos comparável ao groove nem pausa recente, também se usa o limite de 85%. São limiares internos e não uma regra universal para todas as tracks.

A repetição acelerada exige dois intervalos recentes entre 30% e 68% do período original. Kicks fracos rejeitados continuam visíveis como candidatos acústicos, mas não reiniciam a ausência do kick forte, não reescrevem a grade e não alimentam a média aprendida. Um kick forte suficiente ainda pode iniciar o drop mesmo que o roll acelerado tenha acabado de terminar.

## Impacto, ausência e agudos

A recuperação dos graves passa a considerar o pico do próprio ataque. O retorno precisa superar a referência de graves suavizada menos 4 dB e crescer ao menos 7 dB sobre o mínimo do breakdown. Isso evita esperar que uma média de 600 ms alcance o novo nível.

Cerca de oito tempos sem kick forte (limiar 7,5 períodos), ou uma pausa recente, permitem usar uma janela de confirmação de aproximadamente 90 ms, em vez dos 120 ms usuais. Ainda são exigidos forma espectral, decaimento, ataque, energia e alinhamento na grade. Candidatos fora da grade conservam a janela de 120 ms para a correção de fase/BPM continuar usando o perfil completo. A latência total inclui FFT, entrega do áudio, processamento e renderização; não se promete luz no instante exato do ataque.

Oito tempos são uma evidência de contexto, não uma obrigação nem uma previsão de que haverá drop. O relógio Link não cria kicks e não incrementa as oito confirmações reais do pós-drop.

## Pausa antes do drop

Uma queda de pelo menos 8 dB no RMS em relação ao trecho anterior, ou silêncio abaixo de −60 dBFS, mantida por pelo menos cerca de 60 ms, registra uma pausa recente no contexto de breakdown/build-up aprendido. A evidência expira em até um segundo depois do vale, dependendo do período.

Se o silêncio passa de 350 ms, o estado visual é **Silêncio** e as luzes ficam apagadas. Durante uma pausa curta desse contexto, a referência permanece disponível por até 2,5 períodos, limitada à faixa de 0,8–1,5 s. O retorno dentro desse prazo retoma a análise anterior, sem exigir quatro novos kicks. Silêncio longo descarta a referência; fonte/formato novos ou descontinuidade de captura continuam reiniciando os trackers.

Depois do silêncio, a melodia que reaparece junto com o kick não deve ser confundida automaticamente com excesso harmônico de bassline. O detector desconta somente o fundo harmônico aprendido no groove, limitado a 6% da potência do ataque grave. Essa compensação exige pausa recente; os limites de forma, decaimento, potência e grade permanecem. Ataques com harmônicos além desse fundo continuam bloqueados.

## Diagnóstico no palco

A linha de estrutura mostra a potência do último candidato de retorno como porcentagem da média do groove, retornos fracos bloqueados e presença de pausa recente. O motivo do estado informa quando um kick acelerado/fraco foi mantido no build. Passe o mouse sobre o texto para ver o conteúdo completo, sem alterar a geometria do palco.

StructureSnapshot.drop_evidence também publica referência/candidato em dB, razão de potência, tempos ausentes, prontidão, pausa, aceleração, retorno de agudos e motivo. Esses dados acompanham a exportação de diagnóstico JSON.

A análise não identifica literalmente um upfilter nem conhece a estrutura futura da faixa. Mudanças grandes de timbre ou volume entre groove e drop ainda podem exigir evidência adicional. Não há arquivo de áudio real gravado para calibração nesta rodada.
