# Estado da equivalência - 0.2.0-dev.2

A geometria da janela, perfil, zoom e cenas Preview/Programa são guardados no projeto.
Movimento automático e plugins não são reativados ao abrir projetos.

A nova base tem código próprio e uma árvore separada da versão anterior. Não é uma
Release final nem uma implementação equivalente completa. O histórico foi preservado.

| Recurso | Implementação atual | Validação / limite |
|---|---|---|
| Cenas, fontes, camadas, posição, tamanho, opacidade e visibilidade | Integrado à interface | Testes de pixels e persistência |
| Preview/Programa, corte, fade | Integrado | Testes incluindo fade interrompido |
| Vídeo local e RTSP | Integrado | Ficheiro real testado; rede RTSP física não testada |
| Câmera USB, ecrã, janela | Adaptadores DirectShow/GDI integrados | Requer Windows e nomes exatos; hardware pendente |
| Microfone / áudio de dispositivo | Adaptador DirectShow integrado | Hardware pendente |
| Áudio automático de vídeo e RTSP opcional | Integrado | Fontes são descodificadas separadamente do vídeo |
| Mixer por fonte, volume, mute e medidores | Integrado | Testes de ganho, mute, gating por cena e saturação |
| Som do sistema / WASAPI | Adaptador integrado via PyAudioWPatch | Sem teste com dispositivo físico |
| Filtros e ajuste de sincronização | Brilho, contraste, chroma, gate, compressor e atraso de áudio integrados | Testes sintéticos de pixels/PCM; filtros básicos |
| Plugins próprios | API Python de vídeo, ativação explícita | Testes de efeito e desativação por erro; sem compatibilidade binária anterior |
| Monitorização de áudio | Integrada via PortAudio | Dispositivo físico não testado |
| Saída A/V com cadência própria | Integrada | Gravação real e RTMP local testados com ambas as faixas |
| Gravação MKV / RTMP | Integrada | FFmpeg externo; serviço de transmissão real não testado |
| Links web transparentes / CSS | Integrado via Chromium | Transparência e CSS testados em servidor local; sem áudio web |
| Deteção de pessoas / seleção | Integrada via YOLOX/OpenCV DNN; fallback HOG | Modelo verificado por SHA-256; inferência numa imagem pública OpenCV; sem benchmark de vídeo físico |
| Referência persistente / confirmação de recuperação | Integrada | Testes sintéticos de perda, cruzamento e recuperação; não garante identidade real |
| Cinema/Suave/Dinâmico e recorte digital | Integrado | Testes de enquadramento dentro da imagem; qualidade física não validada |
| Troca automática entre câmeras | Experimental e desativada inicialmente | Cinco amostras novas, unicidade e cooldown; apenas imagem, não áudio/PTZ |
| ONVIF | Integrado com descoberta de serviços, autenticação, movimento e presets | Servidor simulado; sem certificação ou testes físicos |
| VISCA IP/Serial e Pelco-D TCP/Serial | Integrados | Pacotes e transporte UDP local testados; sem validação física/ACK VISCA |
| Comandos manuais / presets / deadman | Integrados | Teste de paragem após 350 ms sem atualização + tempo de I/O |
| Joystick físico | Adaptador WinMM integrado | X/Y e botões 1/2; calibração por modelo e hardware pendentes |
| Identidade V / tema / manual | Aplicados ao código, ativos e gerador do PDF | Sem promessa de equivalência visual exata ao mockup |
| Instalador e portable | Workflow de desenvolvimento preparado | Só aprovados se o workflow e teste do executável passarem |

## Ainda falta para equivalência completa

- Validar câmeras, microfones, joystick e serviços reais; medir precisão, latência,
  perda de sinal, recuperação e comportamento de comandos em cada protocolo/modelo.
- Validação física de loopback, áudio de páginas web, filtros avançados, monitorização
  por fonte e compensação automática de relógios de captura. O atraso de áudio é manual.
- Detector/associação avançados e testes de oclusão/cruzamento reais. YOLOX e histograma
  de aparência não têm a mesma qualidade de sistemas avançados de rastreio.
- Encaminhamento de áudio e PTZ por câmera durante handoff. A troca atual substitui a
  imagem da fonte original; mudar de câmera interrompe o PTZ até configuração explícita.
- Equivalência com plugins, filtros e fontes especializadas do motor anterior. Não existe
  compatibilidade binária nem migração automática de projetos.
- Posições dos painéis ajustáveis, tradução completa PT/EN/ES, atualização automática,
  gestão de licenças/assinaturas e integrações externas adicionais.
- Testes prolongados de CPU/memória, recuperação de dispositivos, gravações longas,
  assinatura de código, instalador final e auditoria de dependências distribuídas.

A saída tem um relógio comum de áudio/vídeo. Isso mantém a cadência de saída, mas não
sincroniza automaticamente os relógios das capturas separadas. Não afirmar sincronização
perfeita nem equivalência completa com base apenas nos testes de ficheiros sintéticos.
