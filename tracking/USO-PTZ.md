# Vision Track Studio — protótipo de seleção e rastreamento PTZ

O código da versão preview inclui um painel Qt nativo com vídeo, ligação ONVIF, seleção por retângulo e botão de parar. O motor combina deteção de pessoas por IA (YOLOX), OpenCV CSRT e comparação de aparência. A seleção exige uma pessoa distinta. É rastreio experimental; pessoas semelhantes e oclusões continuam a exigir validação real. A compilação e a validação em hardware determinam a disponibilidade de cada release.

## Painel integrado no Windows
Abra **Painéis → Vision Track • Rastreio PTZ**. Preencha o endereço RTSP, o serviço ONVIF PTZ, o token do perfil, utilizador e senha da câmera. Clique em **Ligar / desligar câmera**. No vídeo do painel, arraste um retângulo à volta do corpo da pessoa. Use **PARAR RASTREIO** para interromper os movimentos. O rastreio para se perder o alvo ou detectar aparência ambígua; selecione novamente para retomar. A senha não é gravada num ficheiro. O vídeo RTSP deste painel é independente das fontes de cena: adicione a mesma câmera como fonte de vídeo para a transmissão.

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
- A IA detecta pessoas; a associação por posição e aparência preserva a seleção da sessão. Não identifica pessoas pelo nome nem garante resolver todas as oclusões.
- O painel controla ONVIF; não inclui VISCA, fallback de câmera fixa, autofocus nem zoom automático. O zoom permanece a zero.
- Só opera em redes/câmaras autorizadas; teste primeiro sem ninguém perto de partes móveis e com velocidades baixas.
- Teste da câmara real, comportamento de encerramento inesperado e watchdog PTZ ainda necessários antes de uso numa live.

## Integração futura
Validação de identidade em cruzamentos reais, descoberta automática ONVIF, VISCA e testes com modelos de câmera reais continuam pendentes. O modelo YOLOX e o helper OpenCV Zoo são Apache-2.0; veja models/LICENSE-YOLOX.txt. Preservar licenças OBS e componentes terceiros.
