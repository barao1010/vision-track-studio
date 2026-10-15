"""GPL-2.0-or-later. Vision Track Studio approved V / viewfinder identity."""
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont

def mark(draw, x, y, size):
    def pts(values):
        return [(x+a*size, y+b*size) for a,b in values]
    draw.polygon(pts([(0,.05),(.26,.05),(.64,.73),(.51,.96)]), fill="#3187FF")
    draw.polygon(pts([(.60,.32),(.87,.32),(.67,.67),(.53,.44)]), fill="#6BB6FF")
    draw.line(pts([(.68,.08),(.98,.08),(.98,.39)]), fill="#6BB6FF", width=max(1,int(size*.065)), joint="curve")

def generate(root):
    root=Path(root)
    image=Image.new("RGBA",(512,512),(11,16,24,255))
    mark(ImageDraw.Draw(image),72,68,368)
    image.save(root/"frontend/forms/images/obs.png")
    image.save(root/"frontend/cmake/windows/obs-studio.ico",sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
    wordmark=Image.new("RGBA",(900,180),(0,0,0,0))
    d=ImageDraw.Draw(wordmark)
    mark(d,8,8,156)
    font_paths=["C:/Windows/Fonts/segoeuib.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    font_path=next((p for p in font_paths if Path(p).exists()),None)
    font=ImageFont.truetype(font_path,62) if font_path else ImageFont.load_default()
    small=ImageFont.truetype(font_path,30) if font_path else ImageFont.load_default()
    d.text((195,26),"VISION TRACK",font=font,fill="#EDF3FC")
    d.text((200,104),"S T U D I O",font=small,fill="#9AAEC8")
    wordmark.save(root/"frontend/forms/images/vision-track-wordmark.png")
    qrc=root/"frontend/forms/obs.qrc"
    text=qrc.read_text(encoding="utf-8")
    anchor="    <file>images/obs.png</file>"
    if anchor not in text:
        raise RuntimeError("Application icon resource anchor missing")
    qrc.write_text(text.replace(anchor,anchor+"\n    <file>images/vision-track-wordmark.png</file>"),encoding="utf-8")
    cpp=root/"frontend/widgets/OBSBasic.cpp"
    text=cpp.read_text(encoding="utf-8")
    anchor="\tSystemTray(true);"
    if text.count(anchor)!=1:
        raise RuntimeError("Main window identity anchor missing")
    text=text.replace(anchor,'''    auto *brand = new QLabel(this);
    brand->setPixmap(QPixmap(QStringLiteral(":/res/images/vision-track-wordmark.png")).scaled(
        180, 36, Qt::KeepAspectRatio, Qt::SmoothTransformation));
    brand->setContentsMargins(8, 2, 16, 2);
    brand->setToolTip(QStringLiteral("Vision Track Studio"));
    menuBar()->setCornerWidget(brand, Qt::TopLeftCorner);
'''+anchor)
    cpp.write_text(text,encoding="utf-8")
    print("Brand applied to window header, taskbar, About dialog, executable and installer icon.")

if __name__=="__main__":
    generate(sys.argv[1])

