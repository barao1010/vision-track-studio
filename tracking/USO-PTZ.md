# Vision Track Studio
## Manual de utilização - edição experimental Windows

### 1. Instalação e identidade
Execute o instalador do Vision Track Studio. O novo símbolo azul V identifica o aplicativo, o atalho, a barra de tarefas e a janela Sobre. Os avisos de licença aplicáveis constam da seção Créditos e licenças.

### 2. Novo painel principal
Cenas e Fontes ficam à esquerda. A pré-visualização ocupa a área central; o programa e as transições ficam ao seu lado. Mixer e controlos de transmissão ficam à direita. O painel inferior reúne vídeo de rastreio, controlos PTZ e ligação à câmera.
Ao atualizar, a nova disposição substitui uma vez o layout antigo. Para reaplicar, abra Painéis e escolha Aplicar novo layout Vision Track. As opções de configuração continuam acessíveis pelo botão Configurações.

### 3. Ligar uma câmera
Adicione a câmera às Fontes para utilizá-la na gravação ou transmissão. O vídeo do painel de rastreio é uma ligação separada: introduza o endereço RTSP fornecido pelo fabricante.
Para ONVIF, indique o serviço PTZ, token do perfil, utilizador e senha da câmera. Para VISCA IP, indique o IP e a porta UDP com cabeçalho VISCA, normalmente 52381. Para VISCA Serial, indique a porta COM e o baud rate correto. Para Pelco-D, indique a ligação serial ou TCP, baud rate e endereço da câmera.
Clique Ligar / desligar câmera. O computador precisa alcançar a câmera na rede. As credenciais são usadas nesta sessão; não partilhe senhas, URLs com credenciais ou capturas que as revelem.

### 4. Selecionar e acompanhar a pessoa
Arraste um retângulo sobre o corpo da pessoa no vídeo do painel. A IA precisa detetar uma pessoa distinta nessa área para iniciar.
A seleção mantém uma referência visual fixa durante a sessão. Quando o alvo desaparece, a câmera para e a seleção é preservada. A recuperação exige três novas deteções consistentes. Depois de um cruzamento ambíguo, exige cinco confirmações e rejeita aparências concorrentes.
Pessoas com aparência semelhante podem exigir nova seleção manual. Esta associação visual não identifica pessoas por nome e não garante identidade absoluta.

### 5. Movimento e controlo manual
Cinema, Suave e Dinâmico alteram resposta, aceleração e margem de movimento. Ajuste Velocidade máxima e inversões dos eixos conforme a instalação. O enquadramento preserva espaço acima do corpo.
Segure uma seta ou Zoom + / Zoom - para mover manualmente. Soltar envia Stop. O controlo manual cancela a seleção; selecione novamente para retomar a IA. PARAR RASTREIO interrompe o movimento e limpa a seleção.
Escolha um número para guardar ou chamar um preset. Posição inicial depende do protocolo e da câmera; Pelco-D não oferece esse comando.

### 6. Áudio, gravação e transmissão
Configure microfones e fontes no mixer nativo. Confirme que os medidores respondem antes de gravar. Configure o serviço de transmissão e faça uma gravação de teste para verificar imagem, som e sincronização.
Iniciar gravação e Iniciar transmissão são operações distintas. Confirme o destino e as configurações antes de iniciar uma live.

### 7. Limitações desta edição
Esta edição tem rastreio PTZ físico por ONVIF, VISCA IP/Serial e Pelco-D. Recorte digital automático de fontes fixas, troca automática entre várias câmeras, joystick físico e descoberta automática ONVIF ainda não estão integrados.
O detector nativo é YOLOX. Os testes automáticos e o teste de arranque não substituem testes no Windows com as câmeras reais, cruzamentos de pessoas, rede, áudio e transmissão.
Uma proposta visual da interface não é uma captura de validação. Consulte a versão publicada e as notas de lançamento antes de atualizar.

### 8. Créditos e licenças
Preserve COPYING, licenças de terceiros e código-fonte correspondente distribuídos com esta edição. OBS Studio é GPL-2.0-ou-posterior; o worker combinado inclui componentes sob GPLv3 e Apache-2.0, conforme LICENSES-TRACKING.md.

