# Modelo de deteção de pessoas

Modelo: object_detection_yolox_2022nov.onnx, OpenCV Zoo / YOLOX.
Origem fixa: opencv/opencv_zoo, commit 47534e27c9851bb1128ccc0102f1145e27f23f98.
SHA-256: c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063.
Tamanho: 35 858 002 bytes. Licença: Apache-2.0; ver LICENSE-YOLOX.txt.

Execute `python -m scripts.fetch_models`. O modelo é descarregado de media.githubusercontent.com,
verificado e incluído pelo workflow no pacote Windows. O binário do modelo não é guardado
na árvore Git; a fonte correspondente e os pesos públicos estão nos links abaixo.

- https://github.com/opencv/opencv_zoo/tree/47534e27c9851bb1128ccc0102f1145e27f23f98/models/object_detection_yolox
- https://github.com/Megvii-BaseDetection/YOLOX

O adaptador usa apenas a classe person do conjunto COCO. A deteção de uma pessoa não
é identificação biométrica nem prova de que é a pessoa previamente selecionada.
O controlo de identidade e a seleção continuam separados. Se o modelo faltar, HOG é
usado com aviso explícito na interface. Modelos diferentes não são aceites silenciosamente.

A resolução padrão de inferência é 416 (equilíbrio CPU/precisão). Nas ações da fonte,
Qualidade do detector permite 320, 416 ou 640. A saída mantém a resolução do projeto;
este ajuste afeta apenas a inferência. Quadros antigos não autorizam movimento PTZ.
