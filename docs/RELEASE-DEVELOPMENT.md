Rascunho interno da base independente de Vision Track Studio. **NÃO PUBLICADO E NÃO APROVADO COMO VERSÃO FINAL.**

Esta revisão inclui mixer/gravação/transmissão A/V, fontes Windows, links/CSS, YOLOX,
seleção de alvo, recuperação conservadora, recorte digital, PTZ, presets e joystick;
também encaminhamento de áudio/PTZ por câmera, reconexão de fontes, painéis ajustáveis e
verificação de atualizações do canal independente.

A aprovação desta revisão exige testes automatizados, build Windows, arranque do executável,
instalação, arranque instalado e desinstalação. Consulte o resultado do workflow específico
da revisão; os testes de protocolo usam servidores simulados/locais.
O detector também é verificado numa imagem pública fixa do OpenCV.

**Não foi validado com câmeras, microfones ou joystick físicos.** A troca de câmeras é
experimental e a aparência semelhante pode confundir a associação de pessoas. Ainda faltam
compatibilidade completa de áudio web, integração comercial de licenças/assinaturas, tradução completa, assinatura e
validação prolongada. Não declarar equivalência completa com a versão anterior.

FFmpeg externo é necessário (PATH ou VISION_TRACK_FFMPEG). O executável FFmpeg não é
incluído. O modelo YOLOX e seus avisos são incluídos no pacote. Consulte o manual e
`docs/PARIDADE.md`; preserve os avisos de dependências distribuídos.
