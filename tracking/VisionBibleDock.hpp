// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <obs.hpp>
#include <cstring>
#include <utility>
#include <QMainWindow>
#ifdef Q_OS_WIN
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif
#include <obs-frontend-api.h>
#include <media-io/audio-resampler.h>
#include <QApplication>
#include <QCheckBox>
#include <QComboBox>
#include <QDockWidget>
#include <QFileDialog>
#include <QFormLayout>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QLabel>
#include <QLineEdit>
#include <QListWidget>
#include <QMutex>
#include <QMutexLocker>
#include <QProcess>
#include <QPushButton>
#include <QSettings>
#include <QTimer>

class VisionBibleDock : public QDockWidget {
    QComboBox *sources;
    QLineEdit *bible;
    QLabel *status, *transcript;
    QListWidget *candidates;
    QCheckBox *automatic;
    QProcess worker;
    QTimer flush;
    QMutex mutex;
    QByteArray audio, pending;
    obs_source_t *capture = nullptr;
    audio_resampler_t *resampler = nullptr;
    QJsonObject current;
    static constexpr const char *textName = "Bíblia IA • Texto";

    void send(const QJsonObject &message) {
        if (worker.state() == QProcess::Running)
            worker.write(QJsonDocument(message).toJson(QJsonDocument::Compact) + '\n');
    }
    static void onAudio(void *param, obs_source_t *, const audio_data *block, bool) {
        auto *self = static_cast<VisionBibleDock *>(param);
        QMutexLocker lock(&self->mutex);
        if (!self->resampler) return;
        uint8_t *output[MAX_AV_PLANES] = {};
        uint32_t frames = 0;
        uint64_t offset = 0;
        if (audio_resampler_resample(self->resampler, output, &frames, &offset,
                                    block->data, block->frames) && output[0]) {
            self->audio.append(reinterpret_cast<const char *>(output[0]), int(frames * 2));
            if (self->audio.size() > 64000) self->audio.remove(0, self->audio.size()-64000);
        }
    }
    void detach() {
        flush.stop();
        if (capture) {
            obs_source_remove_audio_capture_callback(capture, onAudio, this);
            obs_source_release(capture);
            capture = nullptr;
        }
        QMutexLocker lock(&mutex);
        audio.clear();
        audio_resampler_destroy(resampler);
        resampler = nullptr;
    }
    void stop() {
        detach();
        send(QJsonObject{{"action", "quit"}});
        if (worker.state() != QProcess::NotRunning && !worker.waitForFinished(1500)) {
            worker.kill();
            worker.waitForFinished(500);
        }
    }
    void attach() {
        obs_audio_info info{};
        if (!obs_get_audio_info(&info)) { stop(); return; }
        const QByteArray name = sources->currentData().toString().toUtf8();
        capture = obs_get_source_by_name(name.constData());
        if (!capture || !(obs_source_get_output_flags(capture) & OBS_SOURCE_AUDIO)) {
            stop(); status->setText(QStringLiteral("Selecione uma fonte de áudio disponível.")); return;
        }
        resample_info input{info.samples_per_sec, AUDIO_FORMAT_FLOAT_PLANAR, info.speakers};
        resample_info output{16000, AUDIO_FORMAT_16BIT, SPEAKERS_MONO};
        resampler = audio_resampler_create(&output, &input);
        if (!resampler) { stop(); status->setText(QStringLiteral("Falha na conversão do áudio.")); return; }
        obs_source_add_audio_capture_callback(capture, onAudio, this);
        flush.start();
    }
    void display(const QJsonObject &verse) {
        current = verse;
        const QString content = verse["title"].toString() + "\n" + verse["text"].toString();
        OBSSourceAutoRelease output = obs_get_source_by_name(textName);
        if (!output) return;
        OBSDataAutoRelease settings = obs_source_get_settings(output);
        obs_data_set_string(settings, "text", content.toUtf8().constData());
        obs_source_update(output, settings);
    }
    void addToScene() {
        OBSSourceAutoRelease sceneSource = obs_frontend_get_current_scene();
        obs_scene_t *scene = sceneSource ? obs_scene_from_source(sceneSource) : nullptr;
        if (!scene) return;
        OBSSourceAutoRelease output = obs_get_source_by_name(textName);
        if (output && strcmp(obs_source_get_unversioned_id(output), "text_gdiplus") != 0) {
            status->setText(QStringLiteral("Já existe uma fonte com esse nome e outro tipo. Renomeie-a antes de continuar."));
            return;
        }
        if (!output) {
            OBSDataAutoRelease settings = obs_data_create();
            OBSDataAutoRelease font = obs_data_create();
            obs_data_set_string(font, "face", "Arial");
            obs_data_set_int(font, "size", 42);
            obs_data_set_obj(settings, "font", font);
            obs_data_set_string(settings, "text", "Bíblia IA");
            obs_data_set_bool(settings, "extents", true);
            obs_data_set_int(settings, "extents_cx", 1200);
            obs_data_set_int(settings, "extents_cy", 240);
            obs_data_set_bool(settings, "extents_wrap", true);
            output = obs_source_create("text_gdiplus_v2", textName, settings, nullptr);
        }
        if (output && !obs_scene_find_source_recursive(scene, textName)) obs_scene_add(scene, output);
        if (!current.isEmpty()) display(current);
        status->setText(QStringLiteral("Texto adicionado à cena de programa. A fonte permite ajustar posição e estilo."));
    }
public:
    explicit VisionBibleDock(QMainWindow *main) : QDockWidget(QStringLiteral("Bíblia por voz"), main) {
        setObjectName(QStringLiteral("visionBibleDock"));
        setProperty("vtsPanel", true);
        auto *body = new QWidget(this);
        auto *layout = new QFormLayout(body);
        bible = new QLineEdit(body);
        QSettings saved("VisionTrack", "StudioBible");
        bible->setText(saved.value("bible").toString());
        auto *browse = new QPushButton(QStringLiteral("Importar tradução JSON"), body);
        sources = new QComboBox(body);
        auto *refresh = new QPushButton(QStringLiteral("Atualizar fontes de áudio"), body);
        auto *start = new QPushButton(QStringLiteral("Ligar / parar escuta"), body);
        automatic = new QCheckBox(QStringLiteral("Exibir referências e citações confirmadas automaticamente"), body);
        automatic->setChecked(true);
        transcript = new QLabel(QStringLiteral("Aguardando fala."), body); transcript->setWordWrap(true);
        candidates = new QListWidget(body);
        auto *show = new QPushButton(QStringLiteral("Exibir passagem selecionada"), body);
        auto *add = new QPushButton(QStringLiteral("Adicionar texto à cena de programa"), body);
        status = new QLabel(QStringLiteral("Importe apenas uma tradução que tenha autorização para utilizar."), body);
        status->setWordWrap(true);
        layout->addRow(bible); layout->addRow(browse); layout->addRow(sources); layout->addRow(refresh);
        layout->addRow(start); layout->addRow(automatic); layout->addRow(transcript);
        layout->addRow(candidates); layout->addRow(show); layout->addRow(add); layout->addRow(status);
        setWidget(body);
        auto fill = [this]() {
            if (worker.state() != QProcess::NotRunning) return;
            sources->clear();
            obs_enum_sources([](void *ctx, obs_source_t *source) -> bool {
                if (obs_source_get_type(source) == OBS_SOURCE_TYPE_INPUT && (obs_source_get_output_flags(source) & OBS_SOURCE_AUDIO)) {
                    const QString name = QString::fromUtf8(obs_source_get_name(source));
                    static_cast<QComboBox *>(ctx)->addItem(name, name);
                }
                return true;
            }, sources);
        };
        QObject::connect(refresh, &QPushButton::clicked, this, fill); fill();
        QObject::connect(browse, &QPushButton::clicked, this, [this]() {
            if (worker.state() != QProcess::NotRunning) stop();
            const QString path = QFileDialog::getOpenFileName(this, QStringLiteral("Tradução bíblica"), {}, QStringLiteral("JSON (*.json)"));
            if (!path.isEmpty()) bible->setText(path);
        });
        QObject::connect(start, &QPushButton::clicked, this, [this]() {
            if (worker.state() != QProcess::NotRunning) { stop(); status->setText(QStringLiteral("Escuta parada.")); return; }
            if (bible->text().isEmpty() || sources->currentIndex() < 0) {
                status->setText(QStringLiteral("Selecione uma tradução JSON e uma fonte de áudio.")); return;
            }
            QSettings saved("VisionTrack", "StudioBible"); saved.setValue("bible", bible->text());
            pending.clear();
            worker.setProgram(QApplication::applicationDirPath()+"/vision-bible-worker/vision-bible-worker.exe");
            status->setText(QStringLiteral("A carregar o reconhecimento offline…")); worker.start();
        });
#ifdef Q_OS_WIN
        worker.setCreateProcessArgumentsModifier([](QProcess::CreateProcessArguments *args) { args->flags |= CREATE_NO_WINDOW; });
#endif
        QObject::connect(&worker, &QProcess::started, this, [this]() {
            send(QJsonObject{{"bible", bible->text()}, {"model", QApplication::applicationDirPath()+"/vision-bible-worker/_internal/speech-model"}});
        });
        flush.setInterval(100);
        QObject::connect(&flush, &QTimer::timeout, this, [this]() {
            if (worker.bytesToWrite() > 64000) return;
            QByteArray chunk;
            { QMutexLocker lock(&mutex); chunk = std::move(audio); audio.clear(); }
            if (!chunk.isEmpty()) send(QJsonObject{{"action", "audio"}, {"pcm", QString::fromLatin1(chunk.toBase64())}});
        });
        QObject::connect(&worker, &QProcess::readyReadStandardOutput, this, [this]() {
            pending += worker.readAllStandardOutput();
            int line;
            while ((line = pending.indexOf('\n')) >= 0) {
                const auto message = QJsonDocument::fromJson(pending.left(line)).object(); pending.remove(0,line+1);
                if (message.contains("status")) status->setText(message["status"].toString());
                if (message["ready"].toBool()) attach();
                if (message.contains("transcript")) transcript->setText(message["transcript"].toString());
                if (message.contains("suggestions")) {
                    candidates->clear();
                    for (const auto &entry : message["suggestions"].toArray()) {
                        const auto verse = entry.toObject();
                        auto *item = new QListWidgetItem(verse["title"].toString()+" — "+verse["text"].toString(),candidates);
                        item->setData(Qt::UserRole,verse.toVariantMap());
                    }
                }
                if (message.contains("verse")) {
                    current = message["verse"].toObject();
                    if (automatic->isChecked()) display(current);
                    else if (candidates->count() == 0) {
                        auto *item = new QListWidgetItem(current["title"].toString(),candidates);
                        item->setData(Qt::UserRole,current.toVariantMap());
                    }
                }
                if (message["kind"].toString() == "ambiguous") status->setText(QStringLiteral("Passagens semelhantes: escolha a correta para exibir."));
            }
            if (pending.size()>1000000) { stop(); status->setText(QStringLiteral("Resposta inválida do serviço de voz.")); }
        });
        QObject::connect(show, &QPushButton::clicked, this, [this]() {
            auto *item = candidates->currentItem();
            if (item) display(QJsonObject::fromVariantMap(item->data(Qt::UserRole).toMap()));
            else if (!current.isEmpty()) display(current);
        });
        QObject::connect(add, &QPushButton::clicked, this, [this]() { addToScene(); });
        QObject::connect(&worker, &QProcess::readyReadStandardError, this, [this]() { worker.readAllStandardError(); });
        QObject::connect(&worker, &QProcess::errorOccurred, this, [this](QProcess::ProcessError) { detach(); status->setText(QStringLiteral("O serviço de voz não está disponível.")); });
        QObject::connect(&worker, &QProcess::finished, this, [this](int code, QProcess::ExitStatus) { detach(); if (code) status->setText(QStringLiteral("O serviço de voz terminou com erro. Verifique tradução e modelo.")); });
        QObject::connect(qApp, &QCoreApplication::aboutToQuit, this, [this]() { stop(); });
    }
    ~VisionBibleDock() override { stop(); }
};
