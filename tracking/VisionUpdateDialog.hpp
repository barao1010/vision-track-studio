// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "VisionUpdateBuild.hpp"
#include <obs-frontend-api.h>
#include <QApplication>
#include <QDialog>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLabel>
#include <QMainWindow>
#include <QProcess>
#include <QPushButton>
#include <QVBoxLayout>
#ifdef Q_OS_WIN
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

class VisionUpdateDialog : public QDialog {
    QProcess process;
    QLabel *status;
    QPushButton *install;
    QByteArray pending;
    QJsonObject offer;
    QString installer;
    bool manual;
    bool downloading = false;
    static bool outputActive() {
        return obs_frontend_streaming_active() || obs_frontend_recording_active() || obs_frontend_replay_buffer_active() || obs_frontend_virtualcam_active();
    }
    void launchInstaller() {
        if (outputActive()) {
            status->setText(QStringLiteral("Atualização pronta. Termine a transmissão, gravação, replay e câmera virtual antes de instalar."));
            install->setEnabled(true); return;
        }
        if (!QFileInfo::exists(installer)) {
            status->setText(QStringLiteral("O instalador já não está disponível. Verifique novamente.")); return;
        }
        if (!QProcess::startDetached(installer, {"/SILENT", "/NORESTART", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"})) {
            status->setText(QStringLiteral("Não foi possível abrir o instalador.")); install->setEnabled(true); return;
        }
        if (auto *main = parentWidget()) main->close();
    }
    explicit VisionUpdateDialog(QMainWindow *main, bool requested) : QDialog(main), manual(requested) {
        setObjectName(QStringLiteral("visionUpdateDialog"));
        setAttribute(Qt::WA_DeleteOnClose);
        setWindowTitle(QStringLiteral("Atualização • Vision Track Studio"));
        auto *layout = new QVBoxLayout(this);
        status = new QLabel(QStringLiteral("A verificar atualizações…"),this);
        status->setWordWrap(true);
        install = new QPushButton(QStringLiteral("Transferir e instalar atualização"),this);
        install->setEnabled(false);
        auto *close = new QPushButton(QStringLiteral("Fechar"),this);
        layout->addWidget(status); layout->addWidget(install); layout->addWidget(close);
        resize(440,160);
        QObject::connect(close, &QPushButton::clicked, this, &QDialog::close);
#ifdef Q_OS_WIN
        process.setCreateProcessArgumentsModifier([](QProcess::CreateProcessArguments *args) { args->flags |= CREATE_NO_WINDOW; });
#endif
        process.setProgram(QApplication::applicationDirPath()+"/vision-track-worker/vision-track-worker.exe");
        QObject::connect(install, &QPushButton::clicked, this, [this]() {
            if (!installer.isEmpty()) { launchInstaller(); return; }
            if (outputActive()) { status->setText(QStringLiteral("Termine a transmissão, gravação, replay e câmera virtual antes de atualizar.")); return; }
            downloading = true;
            install->setEnabled(false);
            pending.clear();
            status->setText(QStringLiteral("A transferir e verificar a atualização…"));
            process.setArguments({"--update-download",offer["url"].toString(),offer["digest"].toString()});
            process.start();
        });
        QObject::connect(&process, &QProcess::readyReadStandardOutput, this, [this]() { pending += process.readAllStandardOutput(); });
        QObject::connect(&process, &QProcess::readyReadStandardError, this, [this]() { process.readAllStandardError(); });
        QObject::connect(&process, &QProcess::errorOccurred, this, [this](QProcess::ProcessError) {
            status->setText(QStringLiteral("Não foi possível iniciar a verificação de atualizações."));
            if (!manual && !downloading) deleteLater();
        });
        QObject::connect(&process, &QProcess::finished, this, [this](int code, QProcess::ExitStatus) {
            pending += process.readAllStandardOutput();
            const auto message = QJsonDocument::fromJson(pending.trimmed()).object();
            if (code || message.isEmpty() || message["error"].toBool()) {
                status->setText(QStringLiteral("Não foi possível verificar a atualização. Tente novamente mais tarde."));
                if (!manual && !downloading) deleteLater();
                else install->setEnabled(!offer.isEmpty());
                return;
            }
            if (message.contains("installer")) {
                installer = message["installer"].toString();
                install->setText(QStringLiteral("Instalar atualização verificada"));
                launchInstaller(); return;
            }
            offer = message["offer"].toObject();
            if (offer.isEmpty()) {
                status->setText(QStringLiteral("Nenhuma atualização nativa verificada disponível."));
                if (!manual) deleteLater();
            } else {
                status->setText(QStringLiteral("Nova versão disponível: ")+offer["version"].toString());
                install->setEnabled(true); show(); raise();
            }
        });
        process.setArguments({"--update-check",QString::number(VTS_NATIVE_BUILD)});
        process.start();
        if (manual) show();
    }
public:
    static void check(QMainWindow *main, bool manual) {
        if (auto *existing = main->findChild<QDialog *>(QStringLiteral("visionUpdateDialog"))) {
            if (manual) { existing->show(); existing->raise(); }
            return;
        }
        new VisionUpdateDialog(main,manual);
    }
    ~VisionUpdateDialog() override {
        if (process.state() != QProcess::NotRunning) { process.kill(); process.waitForFinished(1000); }
    }
};
