#!/usr/bin/env python3
"""GPL-2.0-or-later. Apply the native dock and isolated Windows identity."""
from pathlib import Path
import shutil
import sys

root = Path(sys.argv[1]).resolve()
project = Path(__file__).resolve().parent.parent

def replace(path, old, new):
    file = root / path
    text = file.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Upstream anchor missing: {path}: {old}")
    file.write_text(text.replace(old, new), encoding="utf-8")

shutil.copy2(project / "tracking/VisionTrackDock.hpp", root / "frontend/widgets/VisionTrackDock.hpp")
replace("frontend/widgets/OBSBasic.cpp", '#include "OBSBasic.hpp"', '#include "OBSBasic.hpp"\n#include "VisionTrackDock.hpp"')
replace("frontend/widgets/OBSBasic.cpp", '\tstartingDockLayout = saveState();',
        '\tauto *visionTrackDock = new VisionTrackDock(this);\n'
        '\taddDockWidget(Qt::RightDockWidgetArea, visionTrackDock);\n'
        '\tui->menuDocks->addAction(visionTrackDock->toggleViewAction());\n'
        '\tstartingDockLayout = saveState();')
replace("frontend/widgets/OBSBasic.cpp", 'name << "OBS ";', 'name << "Vision Track Studio ";')
replace("frontend/widgets/OBSBasic.cpp", '\tTimedCheckForUpdates();', '\t// Vision Track Studio uses its own release channel.')
replace("frontend/widgets/OBSBasic_Updater.cpp", '#include "OBSBasic.hpp"', '#include "OBSBasic.hpp"\n#include <QDesktopServices>\n#include <QUrl>')
replace("frontend/widgets/OBSBasic_Updater.cpp", 'void OBSBasic::CheckForUpdates(bool manualUpdate)\n{',
        'void OBSBasic::CheckForUpdates(bool manualUpdate)\n{\n'
        '\tif (manualUpdate) QDesktopServices::openUrl(QUrl("https://github.com/barao1010/vision-track-studio/releases"));\n'
        '\treturn; // Never replace this distribution with the official OBS binary.\n')
replace("frontend/widgets/OBSBasic_MainControls.cpp", 'void OBSBasic::on_actionRepair_triggered()\n{',
        'void OBSBasic::on_actionRepair_triggered()\n{\n\tCheckForUpdates(true);\n\treturn;\n')
replace("frontend/widgets/OBSBasic_SysTray.cpp", '"OBS Studio"', '"Vision Track Studio"')
replace("frontend/forms/OBSAbout.ui", '<string notr="true">OBS Studio</string>',
        '<string notr="true">Vision Track Studio</string>')
for file in (root / "frontend/data/locale").glob("*.ini"):
    text = file.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.startswith("About.Info="):
            descriptions = {
                "pt-PT": "Vision Track Studio: produção de vídeo e rastreio PTZ por IA.",
                "pt-BR": "Vision Track Studio: produção de vídeo e rastreamento PTZ por IA.",
                "es-ES": "Vision Track Studio: producción de vídeo y seguimiento PTZ mediante IA.",
            }
            description = descriptions.get(file.stem, "Vision Track Studio: video production and AI PTZ tracking.")
            lines[index] = f'About.Info="{description}"\n'
        else:
            lines[index] = line.replace("OBS Studio", "Vision Track Studio")
    file.write_text("".join(lines), encoding="utf-8")
# Keep OBS plugin/data identifiers intact; only isolate configuration paths.
for file in (root / "frontend").rglob("*.cpp"):
    text = file.read_text(encoding="utf-8")
    updated = text.replace('"obs-studio/', '"vision-track-studio/').replace('"/obs-studio/', '"/vision-track-studio/')
    updated = updated.replace('OBS_DATA_PATH "/vision-track-studio/', 'OBS_DATA_PATH "/obs-studio/')
    if updated != text:
        file.write_text(updated, encoding="utf-8")
replace("frontend/CMakeLists.txt", 'OUTPUT_NAME "$<IF:$<PLATFORM_ID:Windows>,obs64,obs>"',
        'OUTPUT_NAME "$<IF:$<PLATFORM_ID:Windows>,vision-track-studio,obs>"')
print("Native PTZ dock and isolated Vision Track Studio identity applied.")
