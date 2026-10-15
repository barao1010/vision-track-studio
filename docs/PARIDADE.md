# Critérios de equivalência

Esta é uma implementação nova em desenvolvimento, não uma versão equivalente completa.
Não inclui fontes, patches, bibliotecas nem plugins do motor anterior na árvore atual.
O histórico do repositório é preservado; esta separação de código não apaga a origem histórica.

| Recurso | Estado da base independente | Evidência / requisito restante |
|---|---|---|
| Cenas, ordem de fontes, posição, tamanho, opacidade, visibilidade | Implementado | Testes de composição e persistência |
| Imagem, texto, cor | Implementado | Testes por pixels; interface a validar no Windows |
| Vídeo local | Implementado | Codificação e descodificação de ficheiro real em teste |
| RTSP | Adaptador implementado | Sem teste de rede/câmera física |
| Preview/programa, corte, fade | Implementado | Testes incluindo transição interrompida |
| Gravação MKV | Implementado, apenas vídeo | MPEG-4 através de FFmpeg externo; sem áudio nesta etapa |
| RTMP | Adaptador implementado, apenas vídeo | Sem validação com serviço de transmissão; encoder externo necessário |
| Identidade persistente e recuperação confirmada | Algoritmo implementado | Testes sintéticos; detector e integração visual pendentes |
| Perfis Cinema/Suave/Dinâmico e recorte digital | Algoritmo implementado | Testes de limites; integração visual pendente |
| Múltiplas câmeras / troca automática | Pendente | Fontes RTSP simultâneas não equivalem a troca inteligente |
| ONVIF, VISCA IP/Serial, Pelco-D e presets | Pendente | Reimplementação de protocolos, watchdog e testes de hardware |
| Joystick físico | Pendente | Mapeamento, calibração, desconexão segura |
| Captura USB/tela/janelas e áudio | Pendente | Adaptadores nativos Windows |
| Mixer, sincronização A/V, monitorização e filtros | Pendente | Motor de áudio e relógio comum |
| Browser source e plugins | Pendente | Sem compatibilidade automática com plugins anteriores |
| Instalador, assinatura e manual final | Pendente | Não é uma Release pronta |

A aprovação de equivalência exige comparação de cenários gravados e equipamentos reais,
incluindo perdas de sinal, cruzamento de pessoas, recuperação, movimentos PTZ, latência,
carga prolongada, sincronização áudio/vídeo e compatibilidade de projetos.
A versão anterior permanece na branch main. Não abrir projetos antigos como se fossem compatíveis.

Limitações desta etapa: composição em CPU; fontes de imagem são redimensionadas à caixa;
texto simples; resolução inicial 1280×720/25 fps; sem relógio A/V nem compensação temporal
de frames descartados. A duração gravada pode divergir do tempo real se o processamento
não mantiver a taxa configurada. Não usar esta etapa em produção.
