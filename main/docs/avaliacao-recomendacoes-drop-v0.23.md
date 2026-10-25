# Avaliação das recomendações de DSP — versão 0.23

Referência: texto fornecido pelo usuário em 25/10/2026. As avaliações qualitativas e os pesos do anexo são hipóteses de projeto, não medidas de confiabilidade nas tracks do usuário.

| Recomendação | Situação anterior | Tratamento nesta versão |
|---|---|---|
| RMS/loudness relativo | Implementado: referência do groove, silêncio e pausa pré-impacto | Preservado como contexto; volume isolado não autoriza drop |
| Retorno dos graves | Implementado: pico do ataque, queda no breakdown e potência real do kick | Preservado; candidato fraco não substitui a referência aprendida |
| Onsets/spectral flux | Fluxo adaptativo já detectava ataques gerais e rolls | Fluxo normalizado agora também acompanha as evidências explícitas de retorno |
| Novidade espectral | Havia bandas/centroide e mudanças de textura, sem uma distância espectral própria no detector de drop | Adicionada distância entre a distribuição de energia de 12 bandas e um fundo adaptativo de 0,9 s; a normalização separa mudança de timbre de simples mudança de ganho |
| Máquina groove → breakdown/build → drop | Implementada, com armamento, potência, timbre, grade e recuperação de ataque | Preservada; oito tempos sem kick forte também armam um contexto interno de retorno quando o baixo permanece alto, sem rotular automaticamente essa bassline como breakdown |
| Score híbrido normalizado | Critérios e evidências existiam separadamente | Adicionado indicador de diagnóstico combinando potência relativa, fluxo/novidade, confiança do ataque e contexto. Não substitui os critérios obrigatórios |
| Impacto imediato versus confirmação posterior | Havia assinatura rápida de 35–55 ms e análise completa do mesmo ataque, mas não uma fase explícita de continuidade do drop | Adicionadas as fases impact/confirmed: a primeira luz continua no primeiro kick aprovado; o terceiro kick acústico único confirma continuidade. O Pixel Studio mistura o contexto anterior durante o impacto ainda provisório |
| Rejeitar impactos isolados/fake drops | Retirada real dos graves encerrava a cena; falhas de confirmação mantinham os oito kicks | Uma retirada sustentada sem continuidade marca o impacto como rejeitado e retoma o contexto anterior. Ausência de novas confirmações com graves sustentados permanece incerta, preservando a proteção contra encurtar um drop real |
| Fronteira de compasso | Grade acústica/Link já validava a janela temporal do kick | Continua sendo evidência complementar. Não se espera o próximo compasso para disparar um kick forte aprovado |
| Aprendizado de máquina | Não implementado | Não adicionado: exige exemplos de áudio anotados e avaliação separada. Os pesos ilustrativos não foram apresentados como um modelo validado |

## O que muda na decisão

Novidade espectral só reforça um candidato que já passou por identidade/ataque e alinhamento. Junto do fluxo positivo, ela pode substituir o apoio de um crash ou de uma pausa na comparação de potência. O limiar de 70% da potência aprendida continua obrigatório nesse caminho. Cadência acelerada conserva o limiar mais exigente de 85%, inclusive quando o espectro muda, para evitar promover kicks fracos do build.

Um intervalo longo sem kick forte pode existir sobre uma bassline ainda alta. Nesse caso o contexto interno fica armado e o retorno do primeiro ataque real pode usar a assinatura rápida. O painel não precisa chamar a bassline de breakdown só porque houve ausência de kick.

As duas confirmações são diferentes: fast_confirmed descreve a assinatura acústica curta do próprio ataque; phase=confirmed descreve a continuidade de três kicks únicos. Não são necessários três kicks para a primeira luz. A contagem de oito posições do drop continua acústica, sem criar kicks a partir do relógio.

## Limites e testes

Foram acrescentadas regressões para retorno sem crash com novidade espectral, rejeição de roll fraco mesmo com novidade, invariância da medida a ganho, mudança de timbre, bassline sustentada sem roll, impacto isolado seguido de retirada e confirmação progressiva sem atrasar o primeiro kick. Os testes existentes de basslines, pausas, assinatura, grade/Link e duração de oito kicks continuam necessários.

Não foram fornecidos arquivos de áudio das tracks que ainda atrasam. Os testes sintéticos ampliam a cobertura, mas não demonstram precisão universal. Também não foi adicionada detecção de drop sem kick: esse caso exigiria outra definição e avaliação, considerando o histórico de falsos positivos com basslines.
