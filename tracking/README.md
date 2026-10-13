# Seguimento PTZ de pessoa selecionada — módulo inicial

O utilizador pediu a função do Vision Track AI: selecionar uma pessoa na imagem e a câmara PTZ acompanhá-la automaticamente.

## O que existe neste commit
- Controlador independente com `select(target_id)`, `update(...)` e `stop()`.
- Uma pessoa explicitamente selecionada é o único alvo.
- Zona morta central, suavização de pan/tilt e limites de velocidade.
- Paragem ao perder o alvo; zoom desativado até calibração.
- Adaptador `PTZOutput` para implementação futura dos comandos reais da câmara.

## O que NÃO está ligado ainda
- Detector de pessoas, atribuição persistente de IDs e clique na pré-visualização OBS.
- Vídeo da câmara, protocolo ONVIF/VISCA, login, permissões e calibração dos eixos.
- UI do OBS e integração real com o frontend/plugin do Vision Track Studio.
- Testes com câmaras reais e instalador.

Para integração verdadeira, o motor de detecção fornece IDs consistentes e bounding boxes por frame; a UI chama `select(id)` ao clicar; um adaptador ONVIF/VISCA envia velocidade para uma câmara autorizada e implementa `stop()`. Nunca colocar credenciais em logs ou no GitHub. O Vision Track AI anterior permanece inalterado.

A interface e o ciclo de vida do OBS são C++/Qt; este módulo Python é apenas um protótipo separável, não um plugin OBS compilado.
