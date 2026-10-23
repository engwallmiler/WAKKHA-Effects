# Validação — fase 6, versão 0.5

Registro: **2026-10-12 (UTC)**. Windows x64, Python 3.12.10, NumPy 2.5.4, SciPy 1.18.1, PySide6 6.12.0 e PyAudioWPatch 0.2.12.9. Nenhuma dependência nova nesta fase.

## Testes automatizados

**180 testes passaram em 18,55 s**, incluindo os 147 casos anteriores. Evidência: resultado-pytest.txt. O histórico da fase 5 está em validacao-fase5.md e resultado-pytest-fase5.txt.

| Área | Verificação acrescentada |
|---|---|
| Inventário e estados | Seis luminárias abstratas, capacidades e grupos A/B; validação de intensidade, cor e posição normalizadas, rejeitando valores inválidos. |
| Kick | Envelope no tempo de aquisição, decaimento e ausência de redisparo por refinamento de um evento antigo. |
| Relógio | Pulsos, previsão durante ausência de callbacks e estados escuros após expiração da referência. |
| Grupos | Alternância A/B por batidas, sem assumir compasso. |
| Movimento | Posições dentro dos limites automáticos e PARs estáticos. |
| Prioridades | Manual substitui automação; master zero e motor desativado não são ignorados; blackout permanece ao trocar efeito. |
| Transições | Interpolação de modo/cor e blackout sem fade. |
| Captura | Parar a fonte zera efeitos musicais; controles de luz não substituem nem interrompem o runtime de áudio ativo. |
| Worker | Execução sem GUI, início/parada idempotentes, encerramento escuro, falhas isoladas e recuperação após alteração de controle. |
| Persistência | Migração v4 → v5 preserva os ajustes de áudio/BPM; parâmetros de luz validados e salvos. Reabertura começa com motor desativado. |
| GUI | Lighting Studio, controle manual, pan/tilt, blackout, troca de efeito, exportação JSON, importação aplicada e fechamento conjunto de workers. |

## Sessão integrada de 12 segundos

Sinal sintético entregue em tempo real, 48 kHz estéreo, blocos de 512, efeito Pulso pelo relógio:

- 1.125 blocos recebidos, zero descartes e zero falhas de continuidade.
- Beat Tracker sincronizado em aproximadamente 120 BPM.
- 719 quadros de iluminação observados e frame final 720; aproximadamente 60 atualizações/s. A janela de medição final informou 61 Hz.
- Tempo máximo observado do processamento de iluminação: 0,69 ms. Último quadro: aproximadamente 0,16 ms.
- Intensidade máxima observada: 0,743, abaixo do master de 0,8.
- Controle manual confirmado sem áudio; blackout permaneceu ativo após troca de efeito.
- Comando de blackout observado em aproximadamente 16 ms nesta execução.
- Worker encerrado e intensidades finais zero.

Evidência: resultado-iluminacao-fase6.json. A renderização Qt ocorreu em paralelo. Tempos por polling e frequência observada não são garantias de latência, estabilidade prolongada ou resposta de hardware. Não houve reprodução sonora, gravação de áudio nem transmissão DMX.

## Inspeção visual

Seis páginas foram renderizadas em 1440 × 960, com dados sintéticos do pipeline. Lighting Studio foi inspecionado: controles, cores, intensidades e posições recebem estados do motor. Evidência: preview-iluminacao.png. A página usa rolagem para acomodar todos os controles e as seis luminárias. O palco virtual ainda não pertence a esta entrega.

## Aprovação do usuário

O usuário aprovou captura/DSP e kicks com Traktor e, depois, relatou resultado satisfatório para o BPM/PLL. Esses relatos registram a avaliação funcional das fases anteriores, sem inventar métricas dessas sessões.

O novo motor precisa ser avaliado no Lighting Studio com a música real do usuário. Sua validação atual é de estados abstratos; não comprova resposta de equipamentos físicos.

## Roteiro desta fase

1. Reiniciar iniciar.cmd, capturar a saída do Traktor e abrir Lighting Studio.
2. Ativar o motor e observar as intensidades em Pulso por kick.
3. Testar Pulso pelo relógio e Alternância A/B após adquirir sincronismo; comparar com o ritmo ouvido.
4. Ajustar master, duração, paleta, transição e velocidade durante a captura.
5. Testar manual, pan/tilt e blackout. Trocar efeito enquanto blackout estiver ativo e confirmar intensidade zero até liberá-lo.
6. Parar a captura e conferir que os efeitos musicais aguardam referência; ambiente/manual continuam disponíveis quando escolhidos explicitamente.
7. Salvar preferências, fechar e reabrir: parâmetros devem permanecer, com o motor inicialmente desativado.

Próxima fase: simulador visual, consumindo os estados do motor. Regras/cenas completas, estrutura musical e DMX seguem a ordem da especificação.
