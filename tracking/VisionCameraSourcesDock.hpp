// SPDX-License-Identifier: GPL-2.0-or-later
// Vision Track Studio 2026-10-14: live OBS camera/source gallery.
#pragma once
#include <QDockWidget>
#include <QHBoxLayout>
#include <QLabel>
#include <QListWidget>
#include <QPushButton>
#include <QVBoxLayout>
#include <QStyle>
#include <obs.h>

class VisionCameraSourcesDock : public QDockWidget {
    QListWidget *cameraList;
    VisionTrackDock *tracking;

public:
    explicit VisionCameraSourcesDock(VisionTrackDock *tracker, QMainWindow *main)
        : QDockWidget(QStringLiteral("Câmeras"), main), tracking(tracker)
    {
        setObjectName(QStringLiteral("visionCameraSourcesDock"));
        auto *root = new QWidget(this);
        auto *layout = new QVBoxLayout(root);
        layout->setContentsMargins(8, 6, 8, 6);
        auto *top = new QHBoxLayout();
        auto *help = new QLabel(QStringLiteral("Fontes de vídeo disponíveis no OBS"), root);
        auto *refresh = new QPushButton(QStringLiteral("Atualizar"), root);
        top->addWidget(help);
        top->addStretch();
        top->addWidget(refresh);
        layout->addLayout(top);
        cameraList = new QListWidget(root);
        cameraList->setViewMode(QListView::IconMode);
        cameraList->setFlow(QListView::LeftToRight);
        cameraList->setWrapping(false);
        cameraList->setIconSize(QSize(44, 44));
        cameraList->setSpacing(7);
        cameraList->setMinimumHeight(88);
        cameraList->setMaximumHeight(116);
        cameraList->setHorizontalScrollMode(QAbstractItemView::ScrollPerPixel);
        cameraList->setStyleSheet(
            "QListWidget {background:#091725;border:1px solid #1D3A53;border-radius:6px;}"
            "QListWidget::item {border:1px solid #28405B;border-radius:6px;"
            "background:#122A40;color:white;padding:8px;min-width:105px;}"
            "QListWidget::item:selected {border:2px solid #1261A8;background:#123B64;}");
        layout->addWidget(cameraList);
        setWidget(root);
        QObject::connect(refresh, &QPushButton::clicked, this, [this]() { refreshList(); });
        QObject::connect(cameraList, &QListWidget::itemClicked, this, [this](QListWidgetItem *item) {
            if (item && tracking)
                tracking->selectFixedSource(item->data(Qt::UserRole).toString());
        });
        refreshList();
    }

    void refreshList()
    {
        const QString previous = cameraList->currentItem()
            ? cameraList->currentItem()->data(Qt::UserRole).toString() : QString();
        cameraList->clear();
        obs_enum_sources([](void *data, obs_source_t *source) -> bool {
            if (obs_source_get_type(source) == OBS_SOURCE_TYPE_INPUT &&
                (obs_source_get_output_flags(source) & OBS_SOURCE_VIDEO)) {
                auto *list = static_cast<QListWidget *>(data);
                const QString name = QString::fromUtf8(obs_source_get_name(source));
                auto *item = new QListWidgetItem(name, list);
                item->setData(Qt::UserRole, name);
                item->setIcon(list->style()->standardIcon(QStyle::SP_ComputerIcon));
                item->setSizeHint(QSize(128, 70));
            }
            return true;
        }, cameraList);
        if (cameraList->count() == 0) {
            auto *item = new QListWidgetItem(QStringLiteral("Adicione câmeras em Fontes"), cameraList);
            item->setFlags(Qt::NoItemFlags);
        }
        for (int i = 0; i < cameraList->count(); ++i) {
            if (cameraList->item(i)->data(Qt::UserRole).toString() == previous)
                cameraList->setCurrentRow(i);
        }
    }
};
