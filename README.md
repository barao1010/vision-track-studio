![Vision Track Studio](assets/vision-track-logo.svg)

# Vision Track Studio

Aplicação Windows para produção de vídeo, gravação, transmissão e rastreio PTZ por IA.

## Estado verificável

O código do painel nativo, o worker de rastreio, as alterações de identidade e o pipeline de instalador estão neste repositório. A compilação publica uma **pré-release experimental** apenas depois dos testes do controlador, build Windows e teste de arranque. Consulte [Actions](https://github.com/barao1010/vision-track-studio/actions) e [Releases](https://github.com/barao1010/vision-track-studio/releases) para saber se há binários concluídos.

Não é uma versão final validada para produção. Áudio, transmissão, plugins, UI e PTZ físico precisam de testes no Windows e com câmeras reais.

## Implementado no código

- Cenas, fontes, mixer, gravação, transmissão e fontes de navegador.
- Painel nativo com vídeo RTSP, serviço ONVIF, credenciais e seleção do alvo por retângulo.
- Botão de parar; interrupção do rastreio quando o alvo é perdido ou a aparência diverge.
- Detector de pessoas por IA (YOLOX/OpenCV Zoo), CSRT e comparação de aparência. A seleção exige uma pessoa distinta; a associação interrompe movimentos em casos ambíguos. Não faz identificação biométrica.
- Identidade no título, metadados Windows, executável, bandeja, ícones, instalador e tela Sobre; configurações próprias.
- Instalador Windows, pacote portable e código-fonte correspondente na pré-release.
- Canal próprio de atualização manual nas Releases.

## Ainda pendente

Validação da associação de alvo em cruzamentos reais, descoberta automática ONVIF, troca de alvo entre câmeras e joystick físico, validação de ponta a ponta em hardware. O rastreio experimental não garante preservar a identidade de pessoas semelhantes.

## Compilar

O workflow fixa a base OBS em `f082210c177a03572cace88c168d0f32d8cde39e`, incluindo submódulos, com checkout superficial. No Windows com as ferramentas oficiais do OBS:

1. Obtenha essa revisão com submódulos.
2. Execute `python scripts/brand_windows.py CAMINHO_OBS` e `python scripts/integrate_studio.py CAMINHO_OBS` neste repositório.
3. Dentro da base OBS, execute `cmake --preset windows-x64 "-DOBS_VERSION_OVERRIDE=33.0.0-rc1-vts-preview"` e `cmake --build --preset windows-x64 --config RelWithDebInfo`.
4. O workflow documenta o empacotamento do worker e do instalador.

Veja [Uso do PTZ](tracking/USO-PTZ.md).

## Licença

OBS Studio é GPL-2.0-ou-posterior. As alterações nativas usam GPL-2.0-ou-posterior. O worker de rastreio combinado é distribuído sob GPLv3, com licenças Apache-2.0 preservadas; veja tracking/LICENSES.md. Preserve autoria, COPYING e licenças de terceiros. O pacote Source exporta a base modificada, submódulos e scripts correspondentes; as dependências mantêm suas próprias licenças.


## Integração do rastreio Vision Track AI

Portados para o worker nativo: seleção persistente, referência de aparência fixa, confirmação em vários quadros após perda/ambiguidade, perfis Cinema/Suave/Dinâmico e composição com margem acima do corpo. Adicionados VISCA IP, VISCA Serial, Pelco-D, setas, zoom manual, presets e posição inicial. O detector continua YOLOX, enquanto o app anterior usa COCO-SSD; a paridade de recursos não é completa. Zoom digital automático integrado na linha de recuperação; várias câmeras e joystick físico permanecem pendentes. Protocolos e comportamento físico exigem validação nas câmeras reais.

## Recuperação da base nativa (16/10/2026)

O ramo `independent-engine` / 0.2.0-dev.3 não tem paridade com o OBS.
Esta linha mantém o motor nativo do OBS na revisão indicada acima, com
identidade própria e disposição dos painéis modificada.

O rastreio recebe quadros da própria fonte do OBS, sem abrir novamente a
câmera USB/placa de captura. Escolha uma fonte em “Fonte de vídeo do OBS”.
No modo fixo, o recorte digital acompanha o alvo na pré-visualização e no
programa e restaura o enquadramento ao parar.

Bíblia por voz e atualização automática continuam pendentes nesta linha nativa.
Câmeras, áudio, transmissão e associação visual exigem validação real.
A recuperação não é uma entrega completa. O pipeline exige agora uma janela
Windows responsiva além de `--version`; isso não comprova produção audiovisual.
