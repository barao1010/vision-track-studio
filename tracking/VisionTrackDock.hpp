// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "FixedCameraSceneZoom.hpp"
#include <QApplication>
#include <QCheckBox>
#include <QComboBox>
#include <QSpinBox>
#include <QGridLayout>
#include <QScrollArea>
#include <QDoubleSpinBox>
#include <QDockWidget>
#include <QFormLayout>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLabel>
#include <QLineEdit>
#include <QMainWindow>
#include <QMouseEvent>
#include <QPainter>
#include <QProcess>
#include <QProcessEnvironment>
#include <QPushButton>
#include <QTimer>
#include <functional>
#include <utility>
#ifdef Q_OS_WIN
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

class VTPreview : public QLabel {
    QPoint start;
    QSize frameSize;
    QRect imageRect;
    QPixmap image;
public:
    std::function<void(QJsonArray)> selected;
    explicit VTPreview(QWidget *parent = nullptr) : QLabel(parent) {
        setMinimumSize(320, 180);
        setText(QStringLiteral("Ligue a câmera para selecionar o alvo."));
        setAlignment(Qt::AlignCenter);
    }
    void setFrame(const QByteArray &bytes) {
        image.loadFromData(bytes, "JPG");
        frameSize = image.size();
        update();
    }
protected:
    void paintEvent(QPaintEvent *event) override {
        if (image.isNull()) { QLabel::paintEvent(event); return; }
        const auto size = image.size().scaled(this->size(), Qt::KeepAspectRatio);
        imageRect = QRect(QPoint((width()-size.width())/2, (height()-size.height())/2), size);
        QPainter painter(this);
        painter.fillRect(rect(), Qt::black);
        painter.drawPixmap(imageRect, image);
    }
    void mousePressEvent(QMouseEvent *event) override {
        start = event->position().toPoint();
    }
    void mouseReleaseEvent(QMouseEvent *event) override {
        const QPoint end = event->position().toPoint();
        if (!selected || !imageRect.contains(start) || !imageRect.contains(end)) return;
        const QRect box = QRect(start, end).normalized();
        const double sx = double(frameSize.width()) / imageRect.width();
        const double sy = double(frameSize.height()) / imageRect.height();
        selected(QJsonArray{int((box.left()-imageRect.left())*sx), int((box.top()-imageRect.top())*sy),
                            int(box.width()*sx), int(box.height()*sy)});
    }
};

class VisionTrackDock : public QDockWidget {
    QProcess worker;
    QLineEdit *video, *ptz, *profile, *user, *password, *host, *serialPort;
    QComboBox *protocol, *motionPreset, *cameraMode, *obsSource;
    FixedCameraSceneZoom sceneZoom;
    QSpinBox *port, *baud, *address, *presetNumber;
    QTimer manualTimer;
    QJsonObject manualCommand;
    QCheckBox *invertPan, *invertTilt;
    QDoubleSpinBox *speed;
    QLabel *status;
    VTPreview *preview;
    QPushButton *connectButton;
    QByteArray pending;
    QTimer watchdog;
    void send(const QJsonObject &message) {
        if (worker.state() == QProcess::Running)
            worker.write(QJsonDocument(message).toJson(QJsonDocument::Compact) + '\n');
    }
    void shutdown() {
        sceneZoom.restore();
        watchdog.stop();
        manualTimer.stop();
        send(QJsonObject{{"action", "quit"}});
        if (!worker.waitForFinished(2500)) {
            worker.kill();
            worker.waitForFinished(500);
        }
    }
public:
    explicit VisionTrackDock(QMainWindow *main) : QDockWidget(QStringLiteral("Rastreamento IA"), main), sceneZoom(static_cast<OBSBasic *>(main)) {
        setObjectName(QStringLiteral("visionTrackDock"));
        auto *body = new QWidget(this);
        auto *layout = new QFormLayout(body);
        layout->setContentsMargins(6, 4, 6, 4);
        layout->setSpacing(6);
        auto *advanced = new QWidget(body);
        auto *advancedLayout = new QFormLayout(advanced);
        advanced->setVisible(false);
        auto *showAdvanced = new QPushButton(QStringLiteral("Ligação e controlos PTZ / opções avançadas ▾"), body);
        QObject::connect(showAdvanced, &QPushButton::clicked, this, [advanced]() {
            advanced->setVisible(!advanced->isVisible());
        });
        cameraMode = new QComboBox(body);
        cameraMode->addItem(QStringLiteral("Câmera PTZ • movimento físico"), QStringLiteral("ptz"));
        cameraMode->addItem(QStringLiteral("Câmera fixa • zoom digital"), QStringLiteral("fixed"));
        layout->addRow(QStringLiteral("Modo de câmera"), cameraMode);
        obsSource = new QComboBox(body);
        auto *refreshSources = new QPushButton(QStringLiteral("Atualizar fontes"), body);
        auto fillSources = [this]() {
            const QString previous = obsSource->currentData().toString();
            obsSource->clear();
            obsSource->addItem(QStringLiteral("Selecione a fonte do OBS"), QString());
            obs_enum_sources([](void *context, obs_source_t *source) -> bool {
                if (obs_source_get_output_flags(source) & OBS_SOURCE_VIDEO) {
                    auto *selector = static_cast<QComboBox *>(context);
                    const QString name = QString::fromUtf8(obs_source_get_name(source));
                    selector->addItem(name, name);
                }
                return true;
            }, obsSource);
            const int index = obsSource->findData(previous);
            if (index >= 0)
                obsSource->setCurrentIndex(index);
        };
        layout->addRow(QStringLiteral("Fonte da cena (zoom digital)"), obsSource);
        layout->addRow(refreshSources);
        QObject::connect(refreshSources, &QPushButton::clicked, this, fillSources);
        QObject::connect(obsSource, &QComboBox::currentIndexChanged, this, [this]() {
            sceneZoom.setSource(obsSource->currentData().toString());
        });
        QObject::connect(cameraMode, &QComboBox::currentIndexChanged, this, [this]() {
            sceneZoom.restore();
            const bool fixed = cameraMode->currentData().toString() == QStringLiteral("fixed");
            status->setText(fixed
                ? QStringLiteral("Zoom digital: selecione a mesma fonte usada na cena do OBS.")
                : QStringLiteral("PTZ físico: configure protocolo e endereço."));
        });
        fillSources();
        protocol = new QComboBox(body);
        protocol->addItem(QStringLiteral("ONVIF"), QStringLiteral("onvif"));
        protocol->addItem(QStringLiteral("VISCA IP (UDP)"), QStringLiteral("visca_ip"));
        protocol->addItem(QStringLiteral("VISCA Serial"), QStringLiteral("visca_serial"));
        protocol->addItem(QStringLiteral("Pelco-D"), QStringLiteral("pelco_d"));
        advancedLayout->addRow(QStringLiteral("Protocolo PTZ"), protocol);
        host = new QLineEdit(body); host->setPlaceholderText(QStringLiteral("192.168.1.100"));
        port = new QSpinBox(body); port->setRange(1, 65535); port->setValue(52381);
        serialPort = new QLineEdit(body); serialPort->setPlaceholderText(QStringLiteral("COM3"));
        baud = new QSpinBox(body); baud->setRange(1200, 115200); baud->setValue(9600);
        address = new QSpinBox(body); address->setRange(1, 255); address->setValue(1);
        advancedLayout->addRow(QStringLiteral("IP / host (VISCA / Pelco)"), host);
        advancedLayout->addRow(QStringLiteral("Porta de rede"), port);
        advancedLayout->addRow(QStringLiteral("Porta serial (COM)"), serialPort);
        advancedLayout->addRow(QStringLiteral("Baud rate"), baud);
        advancedLayout->addRow(QStringLiteral("Endereço Pelco-D"), address);
        QObject::connect(protocol, &QComboBox::currentIndexChanged, this, [this]() {
            const auto kind = protocol->currentData().toString();
            port->setValue(kind == "visca_ip" ? 52381 : kind == "pelco_d" ? 4001 : 80);
            baud->setValue(kind == "pelco_d" ? 2400 : 9600);
            invertTilt->setChecked(kind == "onvif");
        });
        video = new QLineEdit(body); video->setPlaceholderText(QStringLiteral("rtsp://câmera/stream ou device:0 (USB/HDMI)"));
        ptz = new QLineEdit(body); ptz->setPlaceholderText(QStringLiteral("http://câmera/onvif/ptz_service"));
        profile = new QLineEdit(body);
        user = new QLineEdit(body);
        password = new QLineEdit(body); password->setEchoMode(QLineEdit::Password);
        layout->addRow(QStringLiteral("Vídeo RTSP ou dispositivo"), video);
        advancedLayout->addRow(QStringLiteral("Serviço ONVIF PTZ"), ptz);
        advancedLayout->addRow(QStringLiteral("Token do perfil"), profile);
        advancedLayout->addRow(QStringLiteral("Utilizador"), user);
        advancedLayout->addRow(QStringLiteral("Senha"), password);
        invertPan = new QCheckBox(QStringLiteral("Inverter eixo horizontal"), body);
        invertTilt = new QCheckBox(QStringLiteral("Inverter eixo vertical (ONVIF)"), body);
        invertTilt->setChecked(true);
        advancedLayout->addRow(invertPan); advancedLayout->addRow(invertTilt);
        speed = new QDoubleSpinBox(body); speed->setRange(.05, .6); speed->setSingleStep(.05); speed->setValue(.32);
        layout->addRow(QStringLiteral("Velocidade máxima"), speed);
        motionPreset = new QComboBox(body);
        motionPreset->addItem(QStringLiteral("Cinema"), QStringLiteral("cinema"));
        motionPreset->addItem(QStringLiteral("Suave"), QStringLiteral("suave"));
        motionPreset->addItem(QStringLiteral("Dinâmico"), QStringLiteral("dinamico"));
        layout->addRow(QStringLiteral("Perfil de movimento"), motionPreset);
        connectButton = new QPushButton(QStringLiteral("Ligar / desligar câmera"), body);
        layout->addRow(connectButton);
        preview = new VTPreview(body); layout->addRow(preview);
        auto *stop = new QPushButton(QStringLiteral("PARAR RASTREIO"), body); layout->addRow(stop);
        status = new QLabel(QStringLiteral("Pronto. Credenciais guardadas apenas nesta sessão."), body);
        status->setWordWrap(true); layout->addRow(status);
        auto *manualBody = new QWidget(body);
        auto *manualLayout = new QGridLayout(manualBody);
        manualTimer.setInterval(100);
        QObject::connect(&manualTimer, &QTimer::timeout, this, [this]() { send(manualCommand); });
        auto addManual = [this, manualBody, manualLayout](const QString &label, int row, int col, double pan, double tilt, double zoom) {
            auto *button = new QPushButton(label, manualBody);
            manualLayout->addWidget(button, row, col);
            QObject::connect(button, &QPushButton::pressed, this, [this, pan, tilt, zoom]() {
                manualCommand = QJsonObject{{"action", "manual"}, {"pan", pan * speed->value()},
                                             {"tilt", tilt * speed->value()}, {"zoom", zoom * .15}};
                send(manualCommand); manualTimer.start();
            });
            QObject::connect(button, &QPushButton::released, this, [this]() {
                manualTimer.stop(); send(QJsonObject{{"action", "stop"}});
            });
        };
        addManual(QStringLiteral("↑"), 0, 1, 0, -1, 0);
        addManual(QStringLiteral("←"), 1, 0, -1, 0, 0);
        addManual(QStringLiteral("→"), 1, 2, 1, 0, 0);
        addManual(QStringLiteral("↓"), 2, 1, 0, 1, 0);
        addManual(QStringLiteral("Zoom −"), 3, 0, 0, 0, -1);
        addManual(QStringLiteral("Zoom +"), 3, 2, 0, 0, 1);
        advancedLayout->addRow(QStringLiteral("Controlo manual"), manualBody);
        presetNumber = new QSpinBox(body); presetNumber->setRange(1, 127); presetNumber->setValue(1);
        advancedLayout->addRow(QStringLiteral("Número do preset"), presetNumber);
        for (const auto &entry : {std::pair<const char *, const char *>{"Ir ao preset", "preset_recall"},
                                 {"Guardar preset", "preset_save"}, {"Posição inicial", "home"}}) {
            auto *button = new QPushButton(QString::fromUtf8(entry.first), body);
            const QString action = QString::fromUtf8(entry.second);
            advancedLayout->addRow(button);
            QObject::connect(button, &QPushButton::clicked, this, [this, action]() {
                manualTimer.stop(); send(QJsonObject{{"action", action}, {"number", presetNumber->value()}});
            });
        }
        layout->addRow(showAdvanced);
        layout->addRow(advanced);
        auto *scroll = new QScrollArea(this); scroll->setWidgetResizable(true); scroll->setWidget(body);
        setWidget(scroll);
        worker.setProcessChannelMode(QProcess::SeparateChannels);
#ifdef Q_OS_WIN
        worker.setCreateProcessArgumentsModifier([](QProcess::CreateProcessArguments *args) {
            args->flags |= CREATE_NO_WINDOW;
        });
#endif
        watchdog.setInterval(4000);
        watchdog.setSingleShot(true);
        QObject::connect(&watchdog, &QTimer::timeout, this, [this]() {
            shutdown(); status->setText(QStringLiteral("Sem resposta do rastreio. Ligação encerrada."));
        });
        QObject::connect(connectButton, &QPushButton::clicked, this, [this]() {
            if (worker.state() != QProcess::NotRunning) { shutdown(); return; }
            const bool fixed = cameraMode->currentData().toString() == QStringLiteral("fixed");
            const QString kind = protocol->currentData().toString();
            const bool invalidConnection = kind == "onvif" ? (ptz->text().isEmpty() || profile->text().isEmpty())
                : kind == "visca_serial" ? serialPort->text().isEmpty()
                : kind == "pelco_d" ? (host->text().isEmpty() && serialPort->text().isEmpty()) : host->text().isEmpty();
            if (video->text().isEmpty() || (!fixed && invalidConnection) || (fixed && obsSource->currentData().toString().isEmpty())) {
                status->setText(QStringLiteral("Preencha vídeo e os dados de ligação do protocolo selecionado.")); return;
            }
            pending.clear();
            sceneZoom.setSource(fixed ? obsSource->currentData().toString() : QString());
            auto env = QProcessEnvironment::systemEnvironment();
            env.insert("VTS_PTZ_USER", user->text()); env.insert("VTS_PTZ_PASSWORD", password->text());
            worker.setProcessEnvironment(env);
            worker.setProgram(QApplication::applicationDirPath() + "/vision-track-worker/vision-track-worker.exe");
            status->setText(QStringLiteral("A ligar à câmera…"));
            worker.start();
        });
        QObject::connect(&worker, &QProcess::started, this, [this]() {
            send(QJsonObject{{"cameraMode", cameraMode->currentData().toString()},
                             {"video", video->text()}, {"ptz", ptz->text()}, {"profile", profile->text()},
                             {"invertPan", invertPan->isChecked()}, {"invertTilt", invertTilt->isChecked()},
                             {"speed", speed->value()}, {"protocol", protocol->currentData().toString()},
                             {"preset", motionPreset->currentData().toString()}, {"host", host->text()},
                             {"port", port->value()}, {"serial", serialPort->text()}, {"baud", baud->value()},
                             {"address", address->value()}});
            watchdog.start(15000);
        });
        QObject::connect(&worker, &QProcess::errorOccurred, this, [this](QProcess::ProcessError) {
            status->setText(QStringLiteral("Não foi possível iniciar o módulo de rastreio."));
        });
        QObject::connect(&worker, &QProcess::readyReadStandardOutput, this, [this]() {
            pending += worker.readAllStandardOutput();
            int newline;
            while ((newline = pending.indexOf('\n')) >= 0) {
                const auto row = pending.left(newline); pending.remove(0, newline+1);
                const auto message = QJsonDocument::fromJson(row).object();
                if (message.contains("status")) status->setText(message["status"].toString());
                if (message["zoomReset"].toBool(false)) sceneZoom.restore();
                if (message.contains("digitalCrop") && cameraMode->currentData().toString() == QStringLiteral("fixed")) {
                    const QJsonObject crop = message["digitalCrop"].toObject();
                    sceneZoom.apply(crop["left"].toDouble(), crop["top"].toDouble(),
                                    crop["width"].toDouble(), crop["height"].toDouble());
                }
                if (message.contains("frame")) {
                    preview->setFrame(QByteArray::fromBase64(message["frame"].toString().toLatin1()));
                    watchdog.start();
                }
            }
            if (pending.size() > 4000000) shutdown();
        });
        QObject::connect(&worker, &QProcess::readyReadStandardError, this, [this]() { worker.readAllStandardError(); });
        QObject::connect(&worker, &QProcess::finished, this, [this](int, QProcess::ExitStatus) { watchdog.stop(); manualTimer.stop(); sceneZoom.restore(); });
        QObject::connect(stop, &QPushButton::clicked, this, [this]() { manualTimer.stop(); sceneZoom.restore(); send(QJsonObject{{"action", "stop"}}); });
        preview->selected = [this](QJsonArray box) { send(QJsonObject{{"action", "select"}, {"box", box}}); };
        QObject::connect(qApp, &QCoreApplication::aboutToQuit, this, [this]() { shutdown(); });
    }
    void selectFixedSource(const QString &name) {
        // Selection does not start tracking automatically or change OBS scenes.
        if (worker.state() != QProcess::NotRunning)
            shutdown();
        cameraMode->setCurrentIndex(cameraMode->findData(QStringLiteral("fixed")));
        obsSource->clear();
        obsSource->addItem(QStringLiteral("Selecione a fonte do OBS"), QString());
        obs_enum_sources([](void *ctx, obs_source_t *source) -> bool {
            if (obs_source_get_output_flags(source) & OBS_SOURCE_VIDEO) {
                auto *selector = static_cast<QComboBox *>(ctx);
                const QString sourceName = QString::fromUtf8(obs_source_get_name(source));
                selector->addItem(sourceName, sourceName);
            }
            return true;
        }, obsSource);
        const int index = obsSource->findData(name);
        if (index >= 0)
            obsSource->setCurrentIndex(index);
        status->setText(QStringLiteral("Fonte selecionada. Configure o endereço RTSP ou device:0 e ligue a câmera."));
    }

    ~VisionTrackDock() override { shutdown(); }
};

