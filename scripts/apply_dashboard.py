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
    for (auto *panel : {ui->scenesDock, ui->sourcesDock, ui->mixerDock, controlsDock, ui->transitionsDock})
        panel->setProperty("vtsPanel", true);
    if (auto *trackingPanel = findChild<QDockWidget *>(QStringLiteral("visionTrackDock")))
        trackingPanel->setProperty("vtsPanel", true);
    // Scope colours to the main workspace; settings dialogs keep their own styling.
    setStyleSheet(styleSheet() + QStringLiteral(R"VTS(

        QMainWindow#OBSBasic { background: #0b1018; }
        QMainWindow#OBSBasic::separator { background: #0b1018; width: 8px; height: 8px; }
        QDockWidget[vtsPanel="true"] { color: #edf3fc; font-family: "Segoe UI"; font-size: 12px;
            border: 1px solid #273447; border-radius: 8px; }
        QDockWidget[vtsPanel="true"]::title { background: #182230; padding: 10px 12px;
            font-weight: 600; border-bottom: 1px solid #273447; }
        QDockWidget[vtsPanel="true"] QWidget { color: #d9e3f2; }
        QDockWidget[vtsPanel="true"] QPushButton { background: #1c2a3b; color: #edf3fc;
            border: 1px solid #34465d; border-radius: 5px; padding: 7px 10px; min-height: 16px; }
        QDockWidget[vtsPanel="true"] QPushButton:hover { background: #273a52; border-color: #5791db; }
        QDockWidget[vtsPanel="true"] QPushButton:pressed { background: #123e77; }
        QDockWidget[vtsPanel="true"] QPushButton:focus { border: 1px solid #69aaff; }
        QDockWidget[vtsPanel="true"] QPushButton:disabled { color: #8290a3; background: #161f2c; border-color: #263345; }
        QDockWidget[vtsPanel="true"] QLineEdit,
        QDockWidget[vtsPanel="true"] QComboBox,
        QDockWidget[vtsPanel="true"] QSpinBox,
        QDockWidget[vtsPanel="true"] QDoubleSpinBox { background: #101a27; color: #edf3fc;
            border: 1px solid #34465d; border-radius: 5px; padding: 5px; min-height: 18px; }
        QDockWidget[vtsPanel="true"] QLineEdit:focus,
        QDockWidget[vtsPanel="true"] QComboBox:focus { border-color: #428eff; }
        QDockWidget[vtsPanel="true"] QSlider::groove:horizontal { height: 4px; background: #34465d; border-radius: 2px; }
        QDockWidget[vtsPanel="true"] QSlider::sub-page:horizontal { background: #3187ff; border-radius: 2px; }
        QDockWidget[vtsPanel="true"] QSlider::handle:horizontal { width: 12px; margin: -4px 0;
            background: #d7eaff; border-radius: 6px; }
        QWidget#centralwidget, QWidget#canvasEditor, QWidget#previewContainer,
        QWidget#vtsProgramColumn { background: #0b1018; }
        QListWidget#scenes, SourceTree#sources { background: #111b28; border: 1px solid #273447; border-radius: 6px; }
        QListWidget#scenes::item { min-height: 30px; padding: 5px 8px; border-radius: 4px; }
        QListWidget#scenes::item:hover { background: #1d304a; }
        QListWidget#scenes::item:selected { background: #1263d7; color: white; }
        SourceTree#sources::item { min-height: 26px; padding: 2px 6px; }
        SourceTree#sources::item:selected { background: #183f70; color: #ffffff; }
        QLabel#previewLabel { color: #e7edf5; padding: 10px; border-bottom: 2px solid #3187ff; }
        QDockWidget#controlsDock QPushButton { min-height: 28px; font-weight: 600; }
        QDockWidget#controlsDock QPushButton#streamButton { background: #1263d7; border-color: #338bff; color: white; }
        QDockWidget#controlsDock QPushButton#streamButton:hover { background: #2279eb; }
        QDockWidget#controlsDock QPushButton#streamButton[class~="state-active"] { background: #963947; border-color: #d56774; }
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

