# Câmaras e acompanhamento por zoom — Vision Track Studio

Atualização de 14/10/2026. Módulo experimental GPL-2.0-or-later.

## Compatibilidade real

O Studio usa as fontes de vídeo disponíveis no OBS para transmissão e composição. São utilizáveis as câmaras reconhecidas pelo Windows/OBS (webcams UVC, USB e placas de captura HDMI), os fluxos IP suportados por OBS/FFmpeg (como RTSP), e entradas oferecidas por plugins instalados pelo utilizador (como NDI). O rastreio físico PTZ suporta, onde as credenciais e firmware forem compatíveis, ONVIF, VISCA IP, VISCA Serial e Pelco-D.

**Não existe garantia de compatibilidade com todas as câmaras.** Modelos proprietários, aparelhos sem drivers, protocolos não suportados ou streams protegidas exigem testes ou adaptadores.

## Câmara fixa — zoom inteligente

1. Em **Fontes**, adicione a imagem da câmara ao OBS. As câmaras USB/HDMI normalmente aparecem como **Dispositivo de captura de vídeo**; RTSP pode utilizar uma fonte multimédia.
2. Na área **Câmeras** do Studio, escolha a **mesma fonte** que está na cena atual. Isto configura o modo **Câmara fixa • zoom digital**.
3. Em **Rastreamento IA**, indique o fluxo de vídeo do mesmo equipamento: `rtsp://...` para câmara IP ou `device:0` para o primeiro dispositivo de captura Windows; índices variam conforme o computador e dispositivo.
4. Clique em **Ligar câmera** e, no fotograma apresentado, arraste um retângulo em volta da pessoa que deve ser seguida.
5. O rastreador envia enquadramentos normalizados ao OBS. O Studio recorta e redimensiona a fonte selecionada na **cena atual**, mantendo a sua posição e dimensão original no palco de composição.
6. **PARAR RASTREIO**, desligar o worker ou sair do Studio restabelece a transformação/crop original da fonte.

**Atenção:** a câmara fixa não roda fisicamente. É uma ampliação digital do vídeo existente; acima da resolução captada a imagem perde nitidez. O algoritmo conserva o último enquadramento quando a associação ao alvo fica ambígua; não deve trocar automaticamente para outra pessoa.

## Modos de controlo

Em **Câmara PTZ • movimento físico**, continua a usar os comandos da câmara com os protocolos existentes, sem crop digital do OBS. As opções de ligação, IP, utilizador, senha, preset e movimentos manuais continuam no painel expansível. A caixa **Configurações** nativa do OBS não foi modificada.

Para usar NDI, é necessário instalar e validar separadamente um plugin compatível e todas as dependências e licenças aplicáveis. O fluxo NDI não é automaticamente capturado pelo worker Python; esse percurso precisa de um stream RTSP/FFmpeg ou interface de captura que o worker consiga ler.

## Situação de testes

Testes unitários validam limites geométricos, suavização, reset e enquadramento. É indispensável validar **no Windows e em câmaras reais** a correspondência entre imagem do worker e fonte OBS, dispositivo USB correto, diferentes proporções, áudio/vídeo, e comportamento ao perder/reconhecer novamente a pessoa.

O painel Bíblia IA presente nas imagens de referência não significa que o reconhecimento bíblico esteja implementado no código-fonte deste repositório. A integração requer uma implementação e testes próprios.

Distribuição baseada no OBS sob GPL-2.0-ou-posterior. Direitos de autor e avisos de autoria da base e dos terceiros devem ser mantidos; consulte README e tracking/LICENSES.md.
