# Vision Track Studio

Distribuição Windows baseada no código original do OBS Studio, com painel Qt de rastreio PTZ. Projeto independente, sem patrocínio do OBS Project.

## Estado verificável

O código do painel nativo, o worker de rastreio, as alterações de identidade e o pipeline de instalador estão neste repositório. A compilação publica uma **pré-release experimental** apenas depois dos testes do controlador, build Windows e teste de arranque. Consulte [Actions](https://github.com/barao1010/vision-track-studio/actions) e [Releases](https://github.com/barao1010/vision-track-studio/releases) para saber se há binários concluídos.

Não é uma versão final validada para produção. Áudio, transmissão, plugins, UI e PTZ físico precisam de testes no Windows e com câmeras reais.

## Implementado no código

- Base OBS com cenas, fontes, mixer, gravação, transmissão e browser source.
- Painel nativo com vídeo RTSP, serviço ONVIF, credenciais e seleção do alvo por retângulo.
- Botão de parar; interrupção do rastreio quando o alvo é perdido ou a aparência diverge.
- Detector de pessoas por IA (YOLOX/OpenCV Zoo), CSRT e comparação de aparência. A seleção exige uma pessoa distinta; a associação interrompe movimentos em casos ambíguos. Não faz identificação biométrica.
- Identidade no título, metadados Windows, executável, bandeja, ícones, instalador e tela Sobre; configurações isoladas das do OBS.
- Instalador Windows, pacote portable e código-fonte correspondente na pré-release.
- Canal de atualização manual nas Releases. Não instala atualizações oficiais do OBS por cima desta distribuição.

## Ainda pendente

Validação da associação de alvo em cruzamentos reais, descoberta automática ONVIF, recorte digital automático de fontes fixas, troca de alvo entre câmeras e joystick físico, validação de ponta a ponta em hardware. O rastreio experimental não garante preservar a identidade de pessoas semelhantes.

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

Portados para o worker nativo: seleção persistente, referência de aparência fixa, confirmação em vários quadros após perda/ambiguidade, perfis Cinema/Suave/Dinâmico e composição com margem acima do corpo. Adicionados VISCA IP, VISCA Serial, Pelco-D, setas, zoom manual, presets e posição inicial. O detector continua YOLOX, enquanto o app anterior usa COCO-SSD; a paridade de recursos não é completa. Zoom digital automático, várias câmeras e joystick físico permanecem pendentes. Protocolos e comportamento físico exigem validação nas câmeras reais.
