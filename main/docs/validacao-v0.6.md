# Validação — versão 0.6, fases 7–8

Registro: 2026-10-12. Windows x64, Python 3.12.10, NumPy 2.5.4, SciPy 1.18.1, PySide6 6.12.0 e PyAudioWPatch 0.2.12.9. Nenhuma dependência nova.

## Regressão automatizada

**212 testes passaram em 46,10 s**, incluindo os 180 casos da versão anterior. Evidência: resultado-pytest.txt. O registro anterior foi preservado em validacao-fase6.md e resultado-pytest-fase6.txt.

As verificações novas cobrem:

- Groove → breakdown → build-up → drop → groove, com contagem exata de oito kicks e deduplicação de refinamentos.
- Crescimento de tensão por aceleração, agudos e centroide espectral.
- Introdução, silêncio, ausência de kick sem redução de graves, crescimento de hats durante groove e falso kick sem retorno dos graves.
- Expiração do pós-drop sem kicks subsequentes, reset e lacunas de callbacks sem mudança de sequência.
- Pipeline com composição sintética em ganho normal e reduzido a 25%; independência dos filtros de inspeção e preservação de estéreo em oposição de fase.
- Falha estrutural isolada, registro único e recuperação após troca de fonte.
- Blackout/manual/master em estados estruturais e saída escura diante de dados ausentes ou antigos.
- Palco com fachos e posições provenientes de FixtureState, controles compartilhados, renderização diferente no blackout, rolagem em 1100 × 760 e encerramento.
- Persistência da fonte de teste de breakdown/drop e identificação explícita como sintética.

## Sessão em tempo real, palco aberto

O script validate_stage.py executou a aplicação Qt com o modo musical, a composição sintética e o palco visível durante 26 s:

| Medida | Resultado |
|---|---|
| Áudio | 48 kHz, estéreo, blocos de 512 |
| Blocos recebidos | 2.435 |
| Descartes / falhas de continuidade | 0 / 0 |
| Groove aprendido | 4,062 s |
| Breakdown | 8,640 s |
| Build-up | 12,937 s |
| Drop | 20,047 s |
| Retorno ao groove no nono kick | 24,062 s |
| Contagem observada no drop | 1, 2, 3, 4, 5, 6, 7, 8 |
| Motor de iluminação | Aproximadamente 60 Hz; última janela 61 Hz |
| Processamento do último quadro de luz | 0,181 ms |
| Erros de subsistemas | Nenhum |
| Encerramento | Workers encerrados, intensidades finais zero |

Evidência: resultado-palco-fase7-8.json. Imagens reais da sessão: preview-breakdown.png, preview-buildup.png e preview-drop.png. As telas foram inspecionadas em 1440 × 960; a rolagem em janela menor foi testada automaticamente.

## Composição offline

validate_structure.py analisou 28 s de sinal em aproximadamente 8,95 s neste computador. Média de processamento: 3,11 ms/bloco; percentil 99: 7,26 ms. O caminho completo identificou o drop em 20 s, contou oito kicks e voltou ao groove em 24 s. A tensão na subida atingiu aproximadamente 95%; pico de intensidade ao entrar no drop: 0,753, limitado pelo master de 0,8. Nenhuma falha de análise ou continuidade.

Evidência: resultado-estrutura-fase8.json. O teste automatizado também repete a composição em ganho 25%. Esses números não são garantias de latência ou desempenho prolongado; não houve reprodução sonora, gravação de áudio ou transmissão DMX.

## Aprovação e teste com música real

O usuário aprovou captura/DSP, kicks, BPM/PLL e o motor inicial com Traktor e a saída do notebook. A aprovação é funcional e não foi convertida em métricas inventadas. A análise estrutural e o palco desta versão têm validação sintética; ainda precisam ser avaliados com as faixas reais.

1. Reiniciar iniciar.cmd, capturar a saída do Traktor e começar por um groove com kicks regulares.
2. Abrir Stage Preview, clicar em Usar automação musical e Ativar motor.
3. Observar a referência adquirida, a frase relativa e a mudança para breakdown durante a redução dos graves.
4. Comparar a tensão mostrada com a subida de snares/agudos ou riser.
5. Conferir retorno do kick no drop, intensidades mais altas, oito kicks e volta ao groove no nono.
6. Testar blackout, controle manual, master e parada de reprodução; dados antigos não devem manter o drop.
7. Se quiser repetir sem áudio do Windows, selecionar Teste • breakdown e drop no Audio Monitor.

A contagem assume 4/4 e **não detecta o primeiro tempo real do compasso**. Snare e upfilter fornecem evidências espectrais; não são instrumentos identificados individualmente. Cenas/regras completas e saídas DMX continuam nas próximas fases.
