# Beat Tracker — fase 5, versão 0.4

## Referência e organização

O usuário aprovou os kicks da versão 0.3 com o Traktor: relatou detecção quase perfeita e resultado muito satisfatório. A fase 5 consome esses eventos, sem modificar ou realimentar o detector de kicks. music/tracker.py recebe KickEvent e tempo monotônico de aquisição. music/clock.py projeta BeatSnapshot imutável. Não há dependência de Qt, PortAudio ou iluminação nesses módulos.

Como referência conceitual, [Davies e Plumbley, Causal Tempo Tracking of Audio, ISMIR 2004](https://www.ee.columbia.edu/~dpwe/ismir2004/CRFILES/paper226.pdf) descrevem acompanhamento causal, previsão e etapas separadas para período e alinhamento. Este protótipo usa uma implementação própria por intervalos e PLL; não reproduz o método de autocorrelação do artigo.

## Estimação e hipóteses

O histórico bruto conserva até 32 kicks dos últimos 12 segundos. Eventos de confiança inferior a 0,25 são ignorados. O mesmo evento refinado pelo detector de kicks só é ingerido uma vez, usando seu timestamp como identidade.

A partir de quatro eventos, são gerados candidatos de período pelos intervalos entre kicks próximos e suas relações de metade/múltiplos. A faixa preferida de BPM limita os candidatos ativos. As 16 hipóteses mais votadas e o período atual são avaliados contra eventos recentes. O ajuste combina proximidade de fase na grade, contratempos com peso menor, ocupação da grade e intervalos diretamente compatíveis com o período.

A interface apresenta o BPM ativo, sua metade e seu dobro, com ajuste aos eventos e indicação de dentro/fora da faixa preferida. Alternativas que explicam os dados de forma semelhante ou melhor geram uma indicação de ambiguidade e reduzem a confiança exibida. Não existe identificação de métrica a partir dessa contagem. Kicks esparsos podem sustentar mais de uma interpretação igualmente plausível.

## PLL causal

Depois da aquisição, o relógio não é reancorado em cada kick bruto. O tracker compara um novo evento com a batida prevista mais próxima. Eventos dentro de 18% do período podem corrigir a grade:

- Correção de fase: 28% do erro temporal observado.
- Correção de período: 7% do erro, dividida pelo número de batidas transcorridas desde a âncora anterior.
- Limites de período: equivalentes ao BPM mínimo e máximo configurados.

Eventos em contratempos não reajustam a grade principal. Uma hipótese substancialmente diferente precisa de vantagem de ajuste e persistência em três avaliações para provocar nova aquisição. Isso permite acompanhar mudanças graduais e recuperar mudanças maiores sem trocar a hipótese a cada oscilação.

O tempo do kick continua sendo estimado pelo centro da janela de análise. Não há calibração do atraso do filtro, do driver, dos alto-falantes ou de futura iluminação. O erro apresentado é o erro residual do ajuste musical, não uma medida de latência acústica.

## Estados e relógio

| Estado | Comportamento |
|---|---|
| Sem sincronismo | Sem referência válida; BPM e previsão ficam indisponíveis. |
| Adquirindo | Coleta eventos, estima período e ajusta fase; ainda não confirma estabilidade. |
| Sincronizado | Pelo menos três ajustes alinhados após a aquisição, confiança interna suficiente e sem sequência recente de erros excessivos. |
| Estimado | A referência alinhada ficou ausente por mais de 1,5 períodos; o relógio continua por previsão, com confiança decrescente. |

Por padrão, a referência expira após 4 s sem kick alinhado. Ao expirar, o tracker deixa de publicar BPM/fase/previsão ativos e aguarda aquisição nova. Eventos antigos não são reingeridos. Uma aquisição incompleta também expira.

O mesmo cálculo de projeção é usado na análise e na GUI. Assim, mesmo que WASAPI deixe de fornecer blocos durante uma pausa, a apresentação passa a estimada e perde a referência no prazo correto. Após Parar, a apresentação fica congelada e identificada como último resultado. A GUI não controla nem modifica o estado do tracker.

Lacunas de sequência, flags de driver e troca de fonte/formato eliminam o relógio anterior. Uma nova captura cria um tracker novo. BeatSnapshot contém BPM, período, fase, próxima batida, confiança, referências temporais, contagem relativa, erro de ajuste, hipóteses e até 120 pontos de histórico. A contagem pode iniciar outra referência ao readquirir; não representa início de compasso.

Falhas opcionais do tracker são isoladas de medidores, FFT e kicks, com mensagem no painel e diagnóstico e um registro por formato. Outro formato permite nova tentativa. Se o detector de kicks falhar, o tracker recebe ausência de eventos e a referência expira normalmente.

## Configuração e uso

Padrões: 90–160 BPM e manutenção estimada de até 4 s. Limites aceitos: 40–240 BPM, intervalo de pelo menos 10 BPM entre mínimo e máximo e manutenção entre 1–12 s. Preferências JSON v4 preservam captura, DSP e ajustes de kicks dos arquivos v1/v2/v3.

1. Abra Rhythm Monitor durante a captura do Traktor.
2. Aguarde vários kicks regulares. O BPM aparece após pelo menos quatro eventos adequados; sincronização exige confirmação adicional.
3. Compare o BPM com o Traktor e o pulso com o kick ouvido.
4. Faça uma mudança gradual de pitch e observe andamento, fase e confiança.
5. Teste uma pausa curta e depois uma pausa acima do tempo configurado; o estado deve passar a estimado e depois sem sincronismo.
6. Se a interpretação estiver em metade/dobro, ajuste a faixa preferida em Configurações, salve e reinicie a captura.

## Limites

A precisão depende dos kicks recebidos. Erros, síncopes, pausas longas, masterização e mudanças de faixa podem exigir nova aquisição. A confiança é heurística, não probabilidade calibrada. Padrões rítmicos diferentes podem explicar a mesma sequência de kicks. Contagem relativa não identifica downbeat, compasso ou estrutura musical.

A validação atual inclui sinais e eventos sintéticos, jitter, eventos extras, ausência temporária, mudanças de tempo e integração com o detector real. O usuário aprovou o resultado do tracker no cenário de uso do Traktor. Essa aprovação funcional não acrescenta medidas de latência ou acurácia estatística. Evidências em validacao.md.

## Grade contínua a partir da versão 0.10

Este documento descreve o PLL acústico e sua expiração. A grade local de quatro ataques é independente e pode continuar enquanto esse PLL está unlocked. A interface e os efeitos pelo relógio preferem a grade quando disponível; hipóteses e histórico do detector continuam como diagnóstico separado. Ver grid-kicks.md.

Desde a versão 0.17, a seleção de Ableton Link pode fornecer BPM/fase ao relógio efetivo da GUI e dos efeitos. O PLL acústico descrito aqui e suas hipóteses continuam independentes. Configuração e diagnóstico: [ableton-link.md](ableton-link.md).
