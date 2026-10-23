# Show rítmico — 0.11

Para o efeito anterior, selecione **Lighting Studio → Show rítmico · padrões, baixo e camadas → Ativar motor**. Na versão 0.12, o botão do Stage Preview seleciona o novo Show RGBW, descrito em rgbw-show.md. Em Lighting Studio, o efeito é **Show rítmico · padrões, baixo e camadas**. O botão de automação musical anterior continua disponível para comparar o wash contínuo. Salvar preferências de luz preserva o efeito, cores e pesos; o motor começa desativado ao abrir.

## Sequências dos PARs

Os quatro PARs recebem intensidades independentes, com ataque imediato, queda marcada e intervalo de repouso. A referência é a mesma grade local do Rhythm Monitor, inclusive sem kicks. A frase relativa tem oito tempos, assumindo 4/4; não identifica o primeiro tempo real da música. Cada sequência repete seus passos e suas trocas de cor nessa frase.

| Família | Distribuição |
|---|---|
| Perseguição | Um PAR por tempo, da esquerda para a direita |
| Vai e volta | Percorre os PARs e retorna |
| Pares alternados | PARs 01/03 respondem a 02/04 |
| Espelho | Externos respondem aos internos |
| Acumulação | Abre e fecha conjuntos progressivamente |
| Resposta do baixo | Combina pares com respostas individuais |

Ocupação/densidade maior favorece pares, espelho e acumulação. Graves com atividade favorecem resposta do baixo e vai e volta; trechos mais esparsos usam perseguição. A família é revista somente nos limites dos compassos relativos de quatro tempos, com histerese na densidade. Ela não roda aleatoriamente: uma variação avança após uma virada por mudança de textura. As cores dos PARs alternam em tempos inteiros; a paleta de áudio é atualizada nos compassos ou na mudança de estrutura.

## Combinação dos elementos

- **Grid:** determina passo e fase, sem fabricar kicks confirmados. Quando a grade ainda está aprendendo, graves e kicks já modulam os PARs, mas nenhum passo/BPM fictício é exibido.
- **Kicks confirmados:** reforçam o acento do conjunto ativo. O instante da confirmação preserva o pico visual. Candidatos graves rejeitados não viram acentos de kick.
- **Baixo:** envelope e atividade de 30–250 Hz modulam força e respostas espaciais no contratempo. Esse pulso de luz não representa a confirmação de um kick.
- **Densidade:** altera distribuição, largura dos pulsos e luminosidade. O controle Peso da densidade também altera a influência na escolha da família.
- **Novas camadas:** aumentos sustentados de densidade, taxa de ataques, energia grave ou brilho são comparados a uma referência suavizada de três segundos. Após pelo menos 150 ms de aumento suficiente, uma virada de dois tempos é agendada para o próximo tempo inteiro. Há um intervalo de oito tempos entre disparos. O mesmo snapshot repetido ou um ataque isolado não agenda viradas. A próxima seleção de família incorpora a variação.

Graves e densidade são descritores do espectro misturado, não stems nem contagem de instrumentos. Ganho, filtro, entrada de baixo ou outros aumentos sustentados também podem produzir uma virada; o sistema não sabe qual instrumento entrou. Os pesos existentes de kick, baixo e densidade continuam ajustáveis. Mesmo com esses pesos zerados, a sequência básica ainda responde ao grid e à estrutura; para zerar luz, use master ou blackout.

## Tensão e impacto

Breakdown usa respostas espaçadas entre externos e internos, com menor luminosidade. Build-up alterna pares e aumenta o brilho; tensão alta ou rolls rápidos passam de um para dois passos por tempo. Com Cores automáticas, o perfil clareia até próximo do branco. Drop usa acentos largos, conjuntos maiores e cores saturadas durante os oito kicks confirmados definidos pela análise estrutural. Viradas por textura cedem prioridade a essas três cenas.

Os moving heads preservam o movimento musical integrado, guiado por BPM, energia, tensão e textura. O controle Movimento limita sua velocidade; zero congela a posição. Master limita todos os estados; blackout, desativação e manual mantêm prioridade. Áudio antigo, silêncio e captura parada retiram a iluminação automática. Interrupções, reinício do show e correções da grade cancelam viradas pendentes.

No palco, a luminosidade das lentes e dos fachos representa a intensidade calculada. Textos continuam com espaço reservado para preservar a geometria durante mudanças de padrão/estrutura. O padrão, tempo e contador de viradas aparecem no topo; a exportação JSON inclui show_pattern, show_step, show_fills e show_novelty. Este último é um indicador relativo de aumento da textura, não probabilidade.

## Comparar com músicas

Comece com quatro kicks regulares e teste um groove esparso, uma bassline sem kick, entrada de hats/melodias, build-up e drop. Ative Cores automáticas para a variação de paleta e branco; Fixo mantém as duas cores escolhidas, ainda alternando-as no grid. Compare o Show rítmico com a automação anterior e ajuste os pesos sem alterar o detector aprovado.

As fontes Teste • baixo e densidade e Teste • breakdown e drop permitem conferir comportamento sem som reproduzido. scripts/validate_show.py testa as duas separadamente, registra contraste por PAR, cores, viradas, continuidade sem kicks, geometria, processamento e encerramento. Os resultados sintéticos estão em validacao.md; a avaliação em tracks reais continua necessária. Não há saída física DMX ou integração Link.
