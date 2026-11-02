# Grade acústica estável e prioridade ao kick — 0.28

A 0.27 podia aceitar novidade espectral fora de tempo com facilidade demais. Esse ataque podia alimentar o estimador de BPM e ocupar os 180 ms de bloqueio do detector, fazendo perder um kick logo depois. A matriz sintética anterior não cobria esse caso; bons resultados nela não garantiram o resultado em faixas reais.

## Como usar

Feche a versão anterior e abra `iniciar.cmd`. Em **Configurações → BPM e sincronização**, escolha:

- **Automático · BPM inteiro estável**: padrão da aplicação. Quatro ataques regulares adquirem a grade inicial; oito observações acústicas permitem estabilizar o período em um BPM inteiro. A fase continua recebendo pequenas correções. Para mudar o andamento, é necessária evidência persistente, com histerese.
- **BPM fixo informado**: informe o BPM inteiro usado no Traktor. O período usa exatamente `60 / BPM`; os ataques reais adquirem e ajustam a fase. Use quando o andamento da faixa já é conhecido. O valor não cria kicks.
- **Contínuo · permite frações**: mantém o ajuste contínuo do período para faixas com andamento fracionário ou variável.

Pare a captura antes de editar; salve as preferências e inicie a captura novamente. O atalho **BPM e grade →** está no Kick Monitor. Preferências anteriores recebem o modo inteiro sem perder os ajustes existentes.

## O que mudou na análise

O detector conserva os candidatos brutos para inspeção, mas separa os que podem orientar o BPM. Depois de a grade acústica ficar confiável, a procura favorece ataques reais na posição esperada, numa janela de até 12% do período. Um ataque mais fraco, com aumento de energia/fluxo e novidade espectral, pode ser recuperado ali.

Um candidato fora da grade não ocupa o bloqueio dos candidatos válidos. Assim, um baixo que ataque 110 ms antes pode aparecer no diagnóstico sem impedir o kick alinhado que chega em seguida. Antes de adquirir uma grade confiável, a recuperação espectral exige evidência mais forte.

O áudio continua obrigatório: silêncio, baixo sustentado e vibrato não viram kicks só por coincidirem com a previsão. A identidade acústica ainda verifica os candidatos antes da confirmação estrutural. Rolls e ataques fora de tempo permanecem disponíveis ao detector de build-up; ataques fortes só podem propor correção grande da grade depois da verificação de identidade e cadência.

Num groove já estabilizado em inteiro/fixo, a identidade pode examinar a queda curta do transiente com o fundo subtraído. Isso evita exigir que a mixagem inteira decaia como um kick isolado quando há baixo sustentado. A exceção exige alinhamento, confiança acústica, similaridade espectral, ataque de pelo menos 1,5 dB e potência de transiente de pelo menos 40% da referência. Não aprende uma nova referência com esse critério e não libera a confirmação de drops; serve para manter o reconhecimento dos kicks no groove. O retorno de drop conserva os critérios estritos anteriores.

O modo inteiro estabilizado também protege contra deslocar a grade em meio tempo por uma bassline no contratempo. O modo contínuo conserva sua recuperação de fase anterior. Trocas reais de timbre, andamento e fase podem exigir nova aquisição; o modo fixo exige que o operador atualize o BPM quando a música mudar de andamento.

Uma fonte Link válida conserva seu próprio BPM e fase, incluindo frações; a escolha de inteiro/fixo se aplica à estimativa local por áudio. A proteção não depende de Link.

## Como ler os monitores

No **Kick Monitor**, a linha verde inteira significa kick confirmado. Marcas curtas cinza na base são candidatos brutos; guias verticais tracejadas são posições previstas. Marcas amarelas na base indicam tempos avaliados sem confirmação. Previsão e candidato não equivalem a kick.

O **Rhythm Monitor** indica **ESTABILIZANDO BPM** durante a aquisição inteira e mostra o inteiro estabilizado depois. O tooltip conserva a estimativa acústica fracionária. O período efetivo usado pelos efeitos muda junto com o BPM; não há apenas arredondamento visual. A grade continua avançando em trechos sem kick enquanto houver contexto de áudio.

## Verificação e limites

Os ensaios usam sinais sintéticos conhecidos, sem acesso ao áudio da imagem enviada pelo usuário. A regressão acrescenta ataques de baixo 110 ms antes dos kicks, baixo sustentado, ganho variável, jitter, mudanças persistentes de andamento, pausas e reinício após perda de áudio. A comparação com a 0.27 fica em `resultado-grade-audio-v0.27.0.json`; o resultado atual, em `resultado-grade-audio-v0.28.0.json`.

Veja também [validação da entrega](validacao.md). Esses testes não medem precisão no repertório real nem substituem uma comparação auditiva no Traktor. O BPM inteiro é uma hipótese adequada ao modo de uso informado; não é uma propriedade universal das músicas.
