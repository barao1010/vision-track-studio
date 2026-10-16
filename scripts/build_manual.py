"""Build the manual for the independent development edition."""
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from vtrack import __version__
from vtrack.brand import icon

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/Vision-Track-Studio-Manual-PT.pdf'
logo = ROOT / 'assets/vision-track.png'
logo.parent.mkdir(exist_ok=True)
icon(512).save(logo)
regular = next((p for p in [Path('C:/Windows/Fonts/arial.ttf'), Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')] if p.exists()), None)
bold = next((p for p in [Path('C:/Windows/Fonts/arialbd.ttf'), Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')] if p.exists()), None)
if regular and bold:
    pdfmetrics.registerFont(TTFont('VT', str(regular)))
    pdfmetrics.registerFont(TTFont('VT-Bold', str(bold)))
    pdfmetrics.registerFontFamily('VT', normal='VT', bold='VT-Bold', italic='VT', boldItalic='VT-Bold')
else:
    raise RuntimeError('Instale Arial ou DejaVu Sans para gerar o manual')
styles = getSampleStyleSheet()
styles['BodyText'].fontName = 'VT'
styles.add(ParagraphStyle(name='TitleVT', fontName='VT-Bold', fontSize=28, leading=34, textColor=colors.HexColor('#071a3d'), spaceAfter=18))
styles.add(ParagraphStyle(name='SectionVT', fontName='VT-Bold', fontSize=16, leading=21, textColor=colors.HexColor('#1261a8'), spaceBefore=8, spaceAfter=7))
styles['BodyText'].fontSize = 9.5
styles['BodyText'].leading = 13
styles['BodyText'].spaceAfter = 5
story = []
def p(text): story.append(Paragraph(text, styles['BodyText']))
def heading(text): story.append(Paragraph(text, styles['SectionVT']))
def footer(canvas, doc):
    canvas.setStrokeColor(colors.HexColor('#dce4ef'))
    canvas.line(45, 43, 550, 43)
    canvas.setFont('VT', 8)
    canvas.setFillColor(colors.HexColor('#526780'))
    canvas.drawString(45, 30, f'Vision Track Studio | {__version__} | Desenvolvimento')
    canvas.drawRightString(550, 30, str(doc.page))
story.append(Image(str(logo), width=74, height=74, hAlign='LEFT'))
story.append(Spacer(1, 16))
story.append(Paragraph('VISION TRACK<br/>STUDIO', styles['TitleVT']))
p(f'Manual da base independente - {__version__}')
p('<b>Esta edição está em desenvolvimento e ainda não tem equivalência completa com a versão anterior.</b> Não foi validada com câmeras, microfones ou joysticks físicos. Os testes de rede usam servidores locais ou simulados.')
heading('Primeiro arranque')
p('Instale Python 3.12 com Tk, execute <b>python -m pip install -r requirements.txt</b>, <b>python -m playwright install chromium</b> e <b>python -m scripts.fetch_models</b>. Instale FFmpeg separadamente no PATH ou indique o caminho em VISION_TRACK_FFMPEG. Inicie com <b>python -m vtrack</b>.')
p('O pacote Windows de desenvolvimento, quando gerado pelo workflow, inclui o runtime Python. FFmpeg continua a ser uma dependência externa. Este pacote de desenvolvimento não é uma versão final aprovada; a entrega e a publicação ficam condicionadas à validação.')
heading('Fluxo de trabalho')
p('Crie cenas no painel esquerdo. Em Adicionar fonte escolha imagem, texto, cor, vídeo, RTSP, câmera USB, ecrã, janela, microfone, áudio ou link web. Selecione uma fonte para alterar posição, tamanho, opacidade e visibilidade. A última fonte da lista fica por cima.')
p('A pré-visualização permite preparar outra cena. Corte envia imediatamente para Programa; Transição mistura durante 500 ms. Programa é a imagem enviada à gravação e transmissão.')
story.append(PageBreak())
heading('Interface e produção')
screenshot = ROOT / 'assets/desktop.png'
if screenshot.exists():
    image = ImageReader(str(screenshot))
    width, height = image.getSize()
    story.append(Image(str(screenshot), width=400, height=400 * height / width))
    p('Captura da interface real em ambiente de teste. A aparência pode variar entre sistemas.')
else:
    p('A captura da interface será acrescentada pelo workflow de empacotamento após o teste de arranque.')
heading('Áudio e gravação')
p('Vídeos com áudio criam um canal automaticamente. Em RTSP, use Áudio da fonte para ativar a faixa; câmera USB e microfone são fontes separadas. Liste os dispositivos para copiar o nome DirectShow exato. Os medidores mostram o sinal das fontes visíveis na cena em Programa, incluindo a transição.')
p('Selecione a fonte para controlar volume e mute. Monitorizar áudio liga a reprodução no dispositivo de saída padrão; use auscultadores para evitar retorno. Gravar MKV grava vídeo e áudio AAC. A transmissão usa URL RTMP completa e requer encoder libx264 no FFmpeg externo.')
p('As saídas usam um relógio comum para manter a cadência mesmo quando a imagem não muda. A sincronização de captura entre fontes físicas ainda precisa de medição e calibração. Som do sistema (WASAPI) captura a saída padrão do Windows. A monitorização e essa fonte não podem estar ativas em simultâneo para evitar retorno. O adaptador depende de validação física.')
heading('Filtros e plugins')
p('Filtros A/V oferece brilho, contraste, chroma key, gate, compressor e atraso de áudio de 0 a 2000 ms. Os filtros são básicos, sem equivalência com uma cadeia avançada de produção. Plugin de vídeo carrega explicitamente um ficheiro Python da API própria; clique novamente para o remover. Plugins binários de outros motores não são compatíveis. Só execute plugins em que confia.')
heading('Links e CSS')
p('Adicione uma fonte Link web / CSS e introduza um endereço HTTP/HTTPS. Editar fonte / CSS abre o editor. O fundo transparente é preservado. A implementação obtém imagens do Chromium e captura áudio de elementos HTML5 compatíveis. O canal pode ser desligado no botão de áudio da fonte. CORS, conteúdos protegidos e grafos WebAudio próprios podem impedir a captura; não existe equivalência completa com todas as fontes web.')
story.append(PageBreak())
heading('Rastreio e enquadramento')
p('Selecione a fonte de vídeo e clique Detetar na fonte selecionada. As pessoas detetadas aparecem em caixas. Clique numa caixa para fixar a referência de aparência. Perda de sinal ou ambiguidade suspende o alvo; a recuperação exige três observações coerentes, ou cinco após ambiguidade.')
p('O detector usa YOLOX/OpenCV com pesos verificados por checksum; HOG é fallback quando o modelo não está instalado. A deteção não é identificação. Pessoas com roupa parecida, oclusões, iluminação e mudanças de ângulo podem causar perda ou confusão. Os testes sintéticos não demonstram a qualidade de rastreio em eventos reais.')
p('Recorte digital automático mantém a saída no tamanho do projeto, ampliando uma região da câmera fixa. Ajuste o zoom e o perfil Cinema, Suave ou Dinâmico. Zoom digital reduz a resolução útil da imagem.')
heading('PTZ, presets e joystick')
p('Configurar / ligar PTZ permite VISCA IP, VISCA Serial, Pelco-D TCP, Pelco-D Serial e ONVIF. Indique o protocolo, IP/porta ou porta série e baud corretos. ONVIF descobre os serviços através do endpoint indicado e usa credenciais apenas na sessão; não as guarda no projeto.')
p('Setas e zoom funcionam enquanto pressionados. Guardar preset e Chamar preset usam o número escolhido. O movimento automático só atua quando está explicitamente ativo e existe uma deteção recente. Ao perder comandos recentes, a sessão envia paragem. A perda de foco interrompe o movimento automático. A mudança de câmera também o interrompe, exceto na troca PTZ explicitamente autorizada e configurada.')
p('Joystick usa WinMM no Windows: eixos X/Y para pan/tilt e botões 1/2 para zoom. Desconexão interrompe os comandos. A calibração por modelo e a compatibilidade física ainda não foram verificadas.')
heading('Troca de câmeras')
p('Ative deteção nas fontes pretendidas, volte à fonte principal e selecione a pessoa. A opção experimental procura uma correspondência única em outra câmera, exige cinco amostras novas e aplica intervalo mínimo entre trocas. Substitui a imagem da fonte principal pela câmera escolhida. Seguir áudio da câmera encaminha também o som; se a câmera não tiver canal de áudio, essa fonte fica em silêncio. Ligar PTZ da próxima câmera permite mudar a ligação física apenas se estiver configurada nesta sessão e se o movimento automático estava ativo; a câmera anterior recebe paragem antes da troca.')
story.append(PageBreak())
heading('Projetos e atualizações')
p('Guarde projetos em JSON. Endereços de fontes podem conter palavras-passe e chaves em texto; o aplicativo pede confirmação antes de os guardar. Projetos da base anterior não são compatíveis automaticamente.')
p('Dependências: Python/Tk, Pillow (MIT-CMU), NumPy (BSD), OpenCV (Apache-2.0 e componentes de terceiros), Playwright (Apache-2.0/Chromium e terceiros), pyserial (BSD), sounddevice e PyAudioWPatch (MIT/PortAudio) e FFmpeg externo, cuja licença depende da compilação. Consulte docs/DEPENDENCIAS.md e os avisos distribuídos com cada componente.')
p('Os separadores entre painéis podem ser arrastados e as posições ficam no projeto. Capturas de áudio/vídeo tentam religar após perda de sinal, com espera progressiva. Verificar atualizações consulta apenas versões finais do motor independente; downloads exigem SHA-256 e confirmação antes de abrir o instalador. Um repositório privado requer VISION_TRACK_GITHUB_TOKEN no computador, nunca incluído no pacote.')
heading('Estado da validação')
p('O workflow Windows verifica composição, áudio, rastreio por dados de teste, protocolos locais, gravação, transmissão RTMP local, arranque do executável, instalação e desinstalação. O relatório de cada revisão no GitHub é a referência do resultado; compilar não prova compatibilidade com equipamentos físicos.')
p('A aprovação final também requer testes de captura e sincronização em equipamentos reais, perda e recuperação de sinal, rastreio com cruzamentos e oclusões e verificação dos controlos em cada modelo de câmera e joystick utilizado.')
p('Consulte docs/PARIDADE.md: ainda faltam testes físicos, validação de loopback e filtros, compatibilidade de plugins, migração de projetos e validação prolongada de desempenho. Esta documentação não declara equivalência total nem aprovação de produção.')
SimpleDocTemplate(str(OUT), title='Vision Track Studio - Manual da base independente', author='Vision Track Studio', pagesize=(595.28, 841.89), rightMargin=45, leftMargin=45, topMargin=40, bottomMargin=56).build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT)
