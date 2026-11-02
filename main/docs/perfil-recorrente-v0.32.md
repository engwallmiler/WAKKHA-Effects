# Kicks alinhados rejeitados pelo perfil — 0.32

A imagem do teste mostrava uma grade estabilizada em 127 BPM, muitos candidatos e rejeições do perfil, com a grade auxiliar de máximos em 0/3. Há três dependências no código da 0.31 que podiam perpetuar esse sintoma:

- as sementes da grade de máximos tinham que combinar com o perfil antigo;
- a recuperação dessa grade só aprendia no groove/contexto inicial;
- a prioridade acústica da grade exigia confiança de 50%, mas a grade preditiva estabilizada pode chegar ao piso de 40% depois de muitas rejeições.

A imagem não contém o áudio: ela não permite determinar qual comparação falhou em cada kick. O novo diagnóstico registra essa decisão, e um sinal sintético reproduz o bloqueio por mudança de timbre.

## Correção

Além do caminho de máximos da 0.31, o sistema compara **quatro ataques acústicos reais consecutivos sobre a grade**, independentemente do perfil antigo. Usa os descritores já calculados e a janela causal de confirmação normal. Compara assinatura espectral do transiente, potência, cauda e seis amostras de subida/queda. Não produz eventos nas posições previstas sem encontrar ataque.

São exigidos contraste, queda real do corpo grave, confiança acústica e limite conservador de harmônicos. Ataques semelhantes entre os tempos bloqueiam essa recuperação para evitar reaprender rolls acelerados. Uma interrupção ou mudança relevante reinicia a sequência. Os quatro candidatos e oito descritores de contratempo são limitados em memória.

Quando a sequência passa pela validação de fase e espaçamento, o perfil é substituído em uma única operação. O BPM é preservado. A confirmação dos próximos kicks usa novamente a triagem normal, agora com a referência atualizada.

O reaprendizado pode recuperar um sistema que já entrou em breakdown por rejeitar kicks. Nesse caso ele retoma o **groove**, sem fabricar um drop pelo simples fato de ter reaprendido. Os critérios próprios de primeiro impacto de drop continuam funcionando para ataques compatíveis com a referência existente. A recuperação não atua durante a cena de drop.

A grade acústica inteira/manual já estabilizada conserva sua prioridade de busca no piso de 40% de confiança. Isso não é aplicado a um relógio genérico com pouca confiança; validade temporal, período e ataque acústico continuam obrigatórios. Não há alteração do estimador de BPM ou novos FFTs/modelos/dependências.

## Como testar

1. Reinicie a aplicação e a captura. O cabeçalho deve mostrar **v0.32**.
2. Mantenha **BPM inteiro estável**, ou o relógio Link que já utiliza.
3. Observe **Kick Monitor → Reaprendendo perfil 1/4…4/4**. Uma comparação incompatível reinicia essa contagem; o motivo aparece ao lado e no tooltip.
4. Depois da recuperação aparece **Perfil recorrente ativo**, o número de reaprendizados e um evento **Perfil + grade** na tabela. Os kicks posteriores voltam ao sensor normal.

**Grade auxiliar de máximos 0/3** se refere ao caminho de máximos da 0.31. O novo reaprendizado funciona independentemente dela. As linhas verdes são os kicks confirmados; as posições previstas continuam distintas.

## Resultado reproduzível

O sinal mantém 127 BPM, aprende um kick inicial e troca por outro corpo mais largo de 45 Hz, sobre baixo em 105 Hz. Há 28 kicks rotulados. Com a 0.31, apenas os nove iniciais são confirmados e os 19 seguintes são perdidos. Na 0.32 são **24/28 confirmados, zero falsos**, com um reaprendizado e BPM mantido em 127. Quatro ataques na transição ainda são perdidos até que haja evidência suficiente para atualizar a referência.

Baixo sustentado, contratempo e baixo harmônico não produziram reaprendizado nem novos kicks. O roll acelerado conservou os **dois falsos candidatos confirmados que já existiam na 0.31**; a nova recuperação não aprendeu esse padrão e não criou drops. Essa limitação permanece registrada, sem representar uma solução completa para toda confusão entre baixo e kick.

Os testes também cobrem retomada depois de uma pausa, 44,1 kHz/blocos de 113 amostras, banda de kick **40–110 Hz** como a imagem e prioridade a 40% sem criar eventos em silêncio, baixo sustentado ou vibrato.

[Referência 0.31](resultado-recurrent-reference-v0.31.json) · [Atual](resultado-recurrent-v0.32.json) · [Monitor nativo](resultado-recurrent-ui-v0.32.json) · [Imagem](../preview-recurrent-v0.32.png) · [Validação completa](validacao.md).

Os ensaios são sintéticos, sem Traktor, áudio ou LEDs físicos. Para medir a faixa da imagem, é necessário processar o áudio pelo [replay causal com rótulos](replay-causal.md); a imagem sozinha não fornece os descritores espectrais ou a cauda dos ataques.
