# Vision Track Studio — protótipo de seleção e rastreamento PTZ

Este protótipo funcional **separado do OBS** usa OpenCV CSRT, vídeo RTSP e comando ONVIF ContinuousMove. Ainda não é IA de identificação de pessoas: segue o objeto selecionado por retângulo e pode perdê-lo ao mudar a cena. **Não há integração nativa do botão no OBS** até concluir o frontend Qt e teste de compilação.

## Requisitos
Python 3.11+ no Windows, `pip install -r tracking/requirements.txt`. Cámara PTZ com endpoint ONVIF e perfil configurado. O PC deve alcançar a cámara via LAN.

No PowerShell:
```powershell
$env:VTS_PTZ_USER="admin"
$env:VTS_PTZ_PASSWORD="SUA_SENHA"
python tracking/ptz_companion.py --rtsp "rtsp://usuario:senha@192.168.1.99:554/stream1" --ptz-url "http://192.168.1.99/onvif/ptz_service" --profile-token "Profile_1"
```
A URL RTSP e o token ONVIF variam por fabricante. **Não copie passwords para GitHub ou screenshots.** Clique e arraste em redor da pessoa, pressione **S** para parar e **ESC** para sair.

## Limitações e segurança
- O controlador usa comandos de velocidade ONVIF; requer câmera compatível e calibração de eixos. Alguns dispositivos exigem configurações de velocidade diferentes.
- Não há detecção automática de pessoas/identidades: o rastreador CSRT segue a região visual selecionada.
- Não tem integração com OBS, fallback de câmera fixa, suavização cinematográfica, autofocus, zoom automático ou instalador.
- Só opera em redes/câmaras autorizadas; teste primeiro sem ninguém perto de partes móveis e com velocidades baixas.
- Teste da câmara real, comportamento de encerramento inesperado e watchdog PTZ ainda necessários antes de uso numa live.

## Integração futura
Criar dock Qt/C++ OBS (seleção de pessoa) com vídeo selecionado, tracker robusto com IDs, serviço ONVIF/VISCA integrado, e comandos seguros de stop. Preservar licenças OBS e componentes terceiros.
