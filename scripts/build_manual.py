"""GPL-2.0-or-later. Build the branded Studio manual from its maintained PTZ guide."""
from pathlib import Path
from xml.sax.saxutils import escape
import sys
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
font_regular = next((p for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"] if Path(p).exists()), None)
font_bold = next((p for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"] if Path(p).exists()), None)
if font_regular and font_bold:
    pdfmetrics.registerFont(TTFont("BrandRegular", font_regular))
    pdfmetrics.registerFont(TTFont("BrandBold", font_bold))
    pdfmetrics.registerFontFamily("BrandRegular", normal="BrandRegular", bold="BrandBold", italic="BrandRegular", boldItalic="BrandBold")

def logo(c,x,y,scale=1):
    c.saveState()
    c.translate(x,y)
    c.scale(scale,scale)
    c.setFillColor(colors.HexColor("#3187FF"))
    p=c.beginPath()
    for i,(a,b) in enumerate([(0,70),(20,70),(50,18),(40,0)]):
        (p.moveTo if i==0 else p.lineTo)(a,b)
    p.close();c.drawPath(p,fill=1,stroke=0)
    c.setFillColor(colors.HexColor("#6BB6FF"))
    p=c.beginPath()
    for i,(a,b) in enumerate([(47,49),(68,49),(52,23),(41,40)]):
        (p.moveTo if i==0 else p.lineTo)(a,b)
    p.close();c.drawPath(p,fill=1,stroke=0)
    c.setStrokeColor(colors.HexColor("#6BB6FF"));c.setLineWidth(5)
    c.lines([(53,68,76,68),(76,68,76,44)])
    c.restoreState()

def build(source, output):
    styles=getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = "BrandBold" if "Heading" in style.name or style.name == "Title" else "BrandRegular"
    styles.add(ParagraphStyle(name="BrandTitle",fontName="BrandBold",fontSize=27,leading=32,textColor=colors.HexColor("#071A3D"),spaceAfter=18))
    styles["BodyText"].fontSize=10;styles["BodyText"].leading=15
    styles["BodyText"].spaceAfter=8
    for h in ("Heading1","Heading2","Heading3"):
        styles[h].textColor=colors.HexColor("#1261A8")
        styles[h].keepWithNext=True
    story=[Spacer(1,90),Paragraph("VISION TRACK<br/>STUDIO",styles["BrandTitle"]),
           Paragraph("Manual de utilização",styles["Heading1"]),
           Paragraph("Edição experimental · Windows · Português",styles["BodyText"]),
           Spacer(1,18),Paragraph("Ligação às câmeras, seleção do alvo, rastreio por IA e controlo PTZ.",styles["BodyText"]),
           Paragraph("Os testes automáticos não substituem a validação com as suas câmeras. Consulte as limitações descritas neste manual.",styles["BodyText"]),PageBreak()]
    for line in Path(source).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            story.append(Spacer(1,5));continue
        if line.startswith("#"):
            level=min(len(line)-len(line.lstrip("#")),3)
            story.append(Paragraph(escape(line.lstrip("# ")),styles["Heading"+str(level)]))
        else:
            story.append(Paragraph(escape(line).replace("\\n","<br/>"),styles["BodyText"]))
    def decorate(c,doc):
        c.setFillColor(colors.HexColor("#071A3D"));c.rect(0,780,596,62,fill=1,stroke=0)
        logo(c,38,792,.42)
        c.setFillColor(colors.white);c.setFont("BrandBold",12);c.drawString(85,810,"VISION TRACK STUDIO")
        c.setFillColor(colors.HexColor("#526176"));c.setFont("BrandRegular",8)
        c.drawString(38,26,"Vision Track Studio | Manual de utilização")
        c.drawRightString(557,26,str(doc.page))
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(output),pagesize=(595.28,841.89),rightMargin=42,leftMargin=42,topMargin=84,bottomMargin=48,
                         title="Vision Track Studio - Manual de utilização",author="Vision Track Studio")
    doc.build(story,onFirstPage=decorate,onLaterPages=decorate)

if __name__=="__main__":
    build(sys.argv[1],sys.argv[2])

