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

shutil.copy2(project / "tracking/FixedCameraSceneZoom.hpp", root / "frontend/widgets/FixedCameraSceneZoom.hpp")
shutil.copy2(project / "tracking/VisionTrackDock.hpp", root / "frontend/widgets/VisionTrackDock.hpp")
shutil.copy2(project / "tracking/VisionCameraSourcesDock.hpp", root / "frontend/widgets/VisionCameraSourcesDock.hpp")
replace("frontend/widgets/OBSBasic.cpp", '#include "OBSBasic.hpp"', '#include "OBSBasic.hpp"\n#include "VisionTrackDock.hpp"\n#include "VisionCameraSourcesDock.hpp"')
# Set up the user's chosen OBS-style but independently arranged workspace.
# No OBS settings dialog, scene, or saved user configuration is rewritten.
replace("frontend/widgets/OBSBasic.cpp", '\tstartingDockLayout = saveState();',
        '\t// Vision Track Studio workspace layout - modified 2026-10-14.\n'
        '\t// Keep existing OBS scene, source, mixer, transitions and control widgets.\n'
        '\taddDockWidget(Qt::RightDockWidgetArea, ui->mixerDock);\n'
        '\tsplitDockWidget(ui->mixerDock, controlsDock, Qt::Vertical);\n'
        '\tsplitDockWidget(controlsDock, ui->transitionsDock, Qt::Vertical);\n'
        '\tauto *visionTrackDock = new VisionTrackDock(this);\n'
        '\tauto *visionCameraDock = new VisionCameraSourcesDock(visionTrackDock, this);\n'
        '\taddDockWidget(Qt::BottomDockWidgetArea, visionCameraDock);\n'
        '\tsplitDockWidget(visionCameraDock, visionTrackDock, Qt::Vertical);\n'
        '\t// Custom main-window-only blue/navy workstation appearance (2026-10-14).\n'
        '\tsetObjectName(QStringLiteral("VisionTrackStudioMainWindow"));\n'
        '\tsetStyleSheet(QStringLiteral(\n'
        '\t    "QDockWidget { border: 1px solid #1E3951; color: #FFFFFF; }"\n'
        '\t    "QDockWidget::title { background: #11263B; border-bottom: 1px solid #2D4762;"\n'
        '\t    "padding: 6px; color: #FFFFFF; font-weight: 600; }"\n'
        '\t    "QDockWidget QWidget#dockWidgetContents_2,"\n'
        '\t    "QDockWidget QWidget#dockWidgetContents_6 { background: #0C1E30; }"));\n'
        '\tui->mixerDock->setWindowTitle(QStringLiteral("Mixer de Áudio"));\n'
        '\tui->transitionsDock->setWindowTitle(QStringLiteral("Transição"));\n'
        '\tui->menuDocks->addAction(visionCameraDock->toggleViewAction());\n'
        '\tui->menuDocks->addAction(visionTrackDock->toggleViewAction());\n'
        '\tresizeDocks({ui->scenesDock, ui->sourcesDock}, {420, 420}, Qt::Vertical);\n'
        '\tresizeDocks({ui->mixerDock, controlsDock, ui->transitionsDock}, {390, 250, 170}, Qt::Vertical);\n'
        '\tstartingDockLayout = saveState();')
# Reposition the existing small dock at the left to mimic the reference.
replace("frontend/widgets/OBSBasic.cpp",
        'int sideDockWidth = std::min(width() * 30 / 100, 320);',
        'int sideDockWidth = std::min(width() * 24 / 100, 285); // Vision Track Studio 2026-10-14')
replace("frontend/widgets/OBSBasic.cpp",
        '\taddDockWidget(Qt::BottomDockWidgetArea, controlsDock);',
        '\taddDockWidget(Qt::RightDockWidgetArea, controlsDock); // Vision Track Studio 2026-10-14')
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
                "pt-PT": "Vision Track Studio é uma distribuição independente baseada no OBS Studio, com rastreio PTZ por IA.",
                "pt-BR": "Vision Track Studio é uma distribuição independente baseada no OBS Studio, com rastreamento PTZ por IA.",
                "es-ES": "Vision Track Studio es una distribución independiente basada en OBS Studio, con seguimiento PTZ mediante IA.",
            }
            description = descriptions.get(file.stem, "Vision Track Studio is an independent distribution based on OBS Studio, with AI PTZ tracking.")
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
replace("frontend/widgets/OBSBasic.cpp", "\tif (!dockStateStr) {\n\t\ton_resetDocks_triggered(true);", "\tif (!dockStateStr) {\n\t\ton_resetDocks_triggered(true);\n\t\t// Vision Track Studio 2026-10-14: first-launch studio preview/program.\n\t\tif (!IsPreviewProgramMode()) SetPreviewProgramMode(true);")
print("OBS-style workspace, fixed-camera zoom dock and isolated identity applied.")
