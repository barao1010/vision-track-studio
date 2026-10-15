#!/usr/bin/env python3
"""GPL-2.0-or-later. Install the Vision Track dashboard and migrate saved docks."""
from pathlib import Path
import sys

def install(root):
    root = Path(root)
    def replace(path, old, new):
        file = root / path
        text = file.read_text(encoding="utf-8")
        if text.count(old) != 1:
            raise RuntimeError(f"Expected one dashboard anchor in {path}: {old!r}")
        file.write_text(text.replace(old, new), encoding="utf-8")

    replace("frontend/widgets/OBSBasic_StudioMode.cpp",
            "\t\tprogramLayout->addWidget(program);",
            "\t\tprogramLayout->addWidget(program, 3);\n"
            "\t\tprogramLayout->addWidget(programOptions, 0);\n"
            "\t\tprogramWidget->setObjectName(QStringLiteral(\"vtsProgramColumn\"));\n"
            "\t\tprogram->setMinimumSize(160, 90);")
    replace("frontend/widgets/OBSBasic_StudioMode.cpp",
            "\t\tui->previewLayout->addWidget(programOptions);\n"
            "\t\tui->previewLayout->addWidget(programWidget);\n"
            "\t\tui->previewLayout->setAlignment(programOptions, Qt::AlignCenter);",
            "\t\tui->previewLayout->addWidget(programWidget, 2);\n"
            "\t\tui->previewLayout->setStretchFactor(ui->previewContainer, 3);")

    dashboard = r"""
    // Dashboard v2: migrate the old OBS dock arrangement once, including upgrades.
    const auto applyVisionDashboard = [this]() {
        setDockNestingEnabled(true);
        setCorner(Qt::TopLeftCorner, Qt::LeftDockWidgetArea);
        setCorner(Qt::BottomLeftCorner, Qt::LeftDockWidgetArea);
        setCorner(Qt::TopRightCorner, Qt::RightDockWidgetArea);
        setCorner(Qt::BottomRightCorner, Qt::RightDockWidgetArea);
        const QList<QDockWidget *> panels{ui->scenesDock, ui->sourcesDock,
                                          ui->mixerDock, controlsDock, ui->transitionsDock};
        for (auto *panel : panels) {
            removeDockWidget(panel);
            panel->setFloating(false);
        }
        addDockWidget(Qt::LeftDockWidgetArea, ui->scenesDock);
        splitDockWidget(ui->scenesDock, ui->sourcesDock, Qt::Vertical);
        addDockWidget(Qt::RightDockWidgetArea, ui->mixerDock);
        splitDockWidget(ui->mixerDock, controlsDock, Qt::Vertical);
        addDockWidget(Qt::BottomDockWidgetArea, ui->transitionsDock);
        auto *tracking = findChild<QDockWidget *>(QStringLiteral("visionTrackDock"));
        if (tracking) {
            removeDockWidget(tracking);
            tracking->setFloating(false);
            addDockWidget(Qt::BottomDockWidgetArea, tracking);
            splitDockWidget(tracking, ui->transitionsDock, Qt::Horizontal);
            tracking->setWindowTitle(QStringLiteral("Câmeras PTZ • Rastreamento IA"));
            tracking->show();
            resizeDocks({tracking, ui->transitionsDock}, {650, 270}, Qt::Horizontal);
        }
        for (auto *panel : panels)
            panel->show();
        resizeDocks({ui->scenesDock, ui->sourcesDock}, {220, 220}, Qt::Horizontal);
        resizeDocks({ui->scenesDock, ui->sourcesDock}, {420, 420}, Qt::Vertical);
        resizeDocks({ui->mixerDock, controlsDock}, {310, 310}, Qt::Horizontal);
        resizeDocks({ui->mixerDock, controlsDock}, {420, 270}, Qt::Vertical);
        resizeDocks({ui->transitionsDock}, {280}, Qt::Vertical);
        SetPreviewProgramMode(true);
        config_set_bool(App()->GetUserConfig(), "BasicWindow", "VerticalVolumeControl", true);
        emit userSettingChanged("BasicWindow", "VerticalVolumeControl");
        config_set_int(App()->GetUserConfig(), "BasicWindow", "VTSLayoutVersion", 2);
        config_set_bool(App()->GetUserConfig(), "BasicWindow", "SideDocks", true);
        config_set_string(App()->GetUserConfig(), "BasicWindow", "DockState",
                         saveState().toBase64().constData());
        config_save_safe(App()->GetUserConfig(), "tmp", nullptr);
    };
    // Scope colours to the main workspace; settings dialogs keep their own styling.
    setStyleSheet(styleSheet() + QStringLiteral(R"VTS(
        QMainWindow#OBSBasic { background: #0b131b; }
        QMainWindow#OBSBasic::separator { background: #091119; width: 8px; height: 8px; }
        QDockWidget#scenesDock, QDockWidget#sourcesDock, QDockWidget#mixerDock,
        QDockWidget#transitionsDock, QDockWidget#controlsDock, QDockWidget#visionTrackDock
            { color: #f1f5f9; border: 1px solid #2c3c49; border-radius: 5px; }
        QDockWidget::title { background: #192630; padding: 9px 10px; }
        QWidget#centralwidget, QWidget#canvasEditor, QWidget#previewContainer,
        QWidget#vtsProgramColumn { background: #0b141d; }
        QListWidget#scenes, SourceTree#sources { background: #101c26; border: 1px solid #293b49; }
        QListWidget#scenes::item { min-height: 34px; padding: 4px; }
        QListWidget#scenes::item:selected { background: #075de0; border-radius: 4px; }
        QLabel#previewLabel { color: #e7edf5; padding: 8px; border-bottom: 2px solid #1589e9; }
    )VTS"));
    auto *dashboardAction = new QAction(QStringLiteral("Aplicar novo layout Vision Track"), this);
    ui->menuDocks->addAction(dashboardAction);
    connect(dashboardAction, &QAction::triggered, this, applyVisionDashboard);
    if (config_get_int(App()->GetUserConfig(), "BasicWindow", "VTSLayoutVersion") < 2)
        QTimer::singleShot(0, this, applyVisionDashboard);
"""
    replace("frontend/widgets/OBSBasic.cpp", "\tSystemTray(true);", dashboard + "\n\tSystemTray(true);")
    print("Vision Track dashboard v2 installed; saved layouts migrate on first launch.")

if __name__ == "__main__":
    install(sys.argv[1])

