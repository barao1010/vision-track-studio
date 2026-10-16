// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "FixedCameraSceneZoom.hpp"
#include <utility/ScreenshotObj.hpp>
#include <QBuffer>
#include <QPointer>
#include <QApplication>
#include <QCheckBox>
#include <QComboBox>
#include <QSpinBox>
#include <QGridLayout>
#include <QHBoxLayout>
#include <QVBoxLayout>
#include <QGroupBox>
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
    QTimer sourceTimer;
    QPointer<ScreenshotObj> sourceCapture;
    bool useObsFrames = false;
    bool trackingEnabled = false;
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
        trackingEnabled = false;
        sourceTimer.stop();
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
    explicit VisionTrackDock(QMainWindow *main) : QDockWidget(QStringLiteral("Vision Track • Rastreio PTZ"), main), sceneZoom(static_cast<OBSBasic *>(main)) {
        setObjectName(QStringLiteral("visionTrackDock"));
        auto *body = new QWidget(this);
        auto *columns = new QHBoxLayout(body);
        columns->setContentsMargins(12, 12, 12, 12);
        columns->setSpacing(16);
        auto *viewColumn = new QGroupBox(QStringLiteral("Câmera • Selecionar alvo"), body);
        auto *viewLayout = new QVBoxLayout(viewColumn);
        auto *controlColumn = new QGroupBox(QStringLiteral("Rastreamento e controlo PTZ"), body);
        auto *controlLayout = new QFormLayout(controlColumn);
        auto *connectionColumn = new QGroupBox(QStringLiteral("Conexão da câmera"), body);
        auto *layout = new QFormLayout(connectionColumn);
        layout->setFieldGrowthPolicy(QFormLayout::AllNonFixedFieldsGrow);
        controlLayout->setFieldGrowthPolicy(QFormLayout::AllNonFixedFieldsGrow);
        columns->addWidget(viewColumn, 4);
        columns->addWidget(controlColumn, 3);
        columns->addWidget(connectionColumn, 3);
        cameraMode = new QComboBox(body);
        cameraMode->addItem(QStringLiteral("PTZ físico"), QStringLiteral("ptz"));
        cameraMode->addItem(QStringLiteral("Câmera fixa • zoom digital"), QStringLiteral("fixed"));
        controlLayout->addRow(QStringLiteral("Modo"), cameraMode);
        obsSource = new QComboBox(body);
        auto *refreshSources = new QPushButton(QStringLiteral("Atualizar fontes"), body);
        auto fillSources = [this]() {
            const QString previous = obsSource->currentData().toString();
            obsSource->clear();
            obsSource->addItem(QStringLiteral("Vídeo externo RTSP / dispositivo"), QString());
            obs_enum_sources([](void *ctx, obs_source_t *source) -> bool {
                if (obs_source_get_type(source) == OBS_SOURCE_TYPE_INPUT &&
                    (obs_source_get_output_flags(source) & OBS_SOURCE_VIDEO)) {
                    const QString name = QString::fromUtf8(obs_source_get_name(source));
                    static_cast<QComboBox *>(ctx)->addItem(name, name);
                }
                return true;
            }, obsSource);
            const int index = obsSource->findData(previous);
            if (index >= 0) obsSource->setCurrentIndex(index);
        };
        layout->addRow(QStringLiteral("Fonte de vídeo do OBS"), obsSource);
        layout->addRow(refreshSources);
        QObject::connect(refreshSources, &QPushButton::clicked, this, fillSources);
        QObject::connect(obsSource, &QComboBox::currentIndexChanged, this, [this]() { shutdown(); });
        QObject::connect(cameraMode, &QComboBox::currentIndexChanged, this, [this]() { shutdown(); });
        fillSources();
        sourceTimer.setInterval(100);
        QObject::connect(&sourceTimer, &QTimer::timeout, this, [this]() {
            if (!useObsFrames || sourceCapture || worker.state() != QProcess::Running || worker.bytesToWrite() > 200000) return;
            const QByteArray name = obsSource->currentData().toString().toUtf8();
            OBSSourceAutoRelease source = obs_get_source_by_name(name.constData());
            if (!source) { shutdown(); status->setText(QStringLiteral("Fonte removida. Rastreio parado.")); return; }
            const auto w = obs_source_get_width(source);
            const auto h = obs_source_get_height(source);
            if (!w || !h) return;
            ScreenshotObj::Options options;
            options.outputToFile = false;
            options.size = QSize(640, std::max(1, int(640.0 * h / w)));
            sourceCapture = new ScreenshotObj(source, options);
            QObject::connect(sourceCapture, &ScreenshotObj::imageReady, this, [this](const QImage &image) {
                if (!sourceTimer.isActive() || image.isNull()) return;
                QByteArray bytes;
                QBuffer buffer(&bytes);
                buffer.open(QIODevice::WriteOnly);
                image.save(&buffer, "JPG", 75);
                send(QJsonObject{{"action", "frame"}, {"frame", QString::fromLatin1(bytes.toBase64())}});
            });
        });
        protocol = new QComboBox(body);
        protocol->addItem(QStringLiteral("ONVIF"), QStringLiteral("onvif"));
        protocol->addItem(QStringLiteral("VISCA IP (UDP)"), QStringLiteral("visca_ip"));
        protocol->addItem(QStringLiteral("VISCA Serial"), QStringLiteral("visca_serial"));
        protocol->addItem(QStringLiteral("Pelco-D"), QStringLiteral("pelco_d"));
        layout->addRow(QStringLiteral("Protocolo PTZ"), protocol);
        host = new QLineEdit(body); host->setPlaceholderText(QStringLiteral("192.168.1.100"));
        port = new QSpinBox(body); port->setRange(1, 65535); port->setValue(52381);
        serialPort = new QLineEdit(body); serialPort->setPlaceholderText(QStringLiteral("COM3"));
        baud = new QSpinBox(body); baud->setRange(1200, 115200); baud->setValue(9600);
        address = new QSpinBox(body); address->setRange(1, 255); address->setValue(1);
        layout->addRow(QStringLiteral("IP / host (VISCA / Pelco)"), host);
        layout->addRow(QStringLiteral("Porta de rede"), port);
        layout->addRow(QStringLiteral("Porta serial (COM)"), serialPort);
        layout->addRow(QStringLiteral("Baud rate"), baud);
        layout->addRow(QStringLiteral("Endereço Pelco-D"), address);
        QObject::connect(protocol, &QComboBox::currentIndexChanged, this, [this]() {
            const auto kind = protocol->currentData().toString();
            port->setValue(kind == "visca_ip" ? 52381 : kind == "pelco_d" ? 4001 : 80);
            baud->setValue(kind == "pelco_d" ? 2400 : 9600);
            invertTilt->setChecked(kind == "onvif");
        });
        video = new QLineEdit(body); video->setPlaceholderText(QStringLiteral("rtsp://câmera/stream ou device:0"));
        ptz = new QLineEdit(body); ptz->setPlaceholderText(QStringLiteral("http://câmera/onvif/ptz_service"));
        profile = new QLineEdit(body);
        user = new QLineEdit(body);
        password = new QLineEdit(body); password->setEchoMode(QLineEdit::Password);
        layout->addRow(QStringLiteral("Vídeo RTSP"), video);
        layout->addRow(QStringLiteral("Serviço ONVIF PTZ"), ptz);
        layout->addRow(QStringLiteral("Token do perfil"), profile);
        layout->addRow(QStringLiteral("Utilizador"), user);
        layout->addRow(QStringLiteral("Senha"), password);
        invertPan = new QCheckBox(QStringLiteral("Inverter eixo horizontal"), body);
        invertTilt = new QCheckBox(QStringLiteral("Inverter eixo vertical (ONVIF)"), body);
        invertTilt->setChecked(true);
        controlLayout->addRow(invertPan); controlLayout->addRow(invertTilt);
        speed = new QDoubleSpinBox(body); speed->setRange(.05, .6); speed->setSingleStep(.05); speed->setValue(.32);
        controlLayout->addRow(QStringLiteral("Velocidade máxima"), speed);
        motionPreset = new QComboBox(body);
        motionPreset->addItem(QStringLiteral("Cinema"), QStringLiteral("cinema"));
        motionPreset->addItem(QStringLiteral("Suave"), QStringLiteral("suave"));
        motionPreset->addItem(QStringLiteral("Dinâmico"), QStringLiteral("dinamico"));
        controlLayout->addRow(QStringLiteral("Perfil de movimento"), motionPreset);
        connectButton = new QPushButton(QStringLiteral("Ligar / desligar câmera"), body);
        layout->addRow(connectButton);
        preview = new VTPreview(viewColumn); viewLayout->addWidget(preview, 1);
        auto *stop = new QPushButton(QStringLiteral("PARAR RASTREIO"), body); controlLayout->addRow(stop);
        status = new QLabel(QStringLiteral("Pronto. Credenciais guardadas apenas nesta sessão."), body);
        status->setWordWrap(true); viewLayout->addWidget(status);
        auto *manualBody = new QWidget(body);
        auto *manualLayout = new QGridLayout(manualBody);
        manualTimer.setInterval(100);
        QObject::connect(&manualTimer, &QTimer::timeout, this, [this]() { send(manualCommand); });
        auto addManual = [this, manualBody, manualLayout](const QString &label, int row, int col, double pan, double tilt, double zoom) {
            auto *button = new QPushButton(label, manualBody);
            manualLayout->addWidget(button, row, col);
            QObject::connect(button, &QPushButton::pressed, this, [this, pan, tilt, zoom]() {
                trackingEnabled = false;
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
        controlLayout->addRow(QStringLiteral("Controlo manual"), manualBody);
        presetNumber = new QSpinBox(body); presetNumber->setRange(1, 127); presetNumber->setValue(1);
        controlLayout->addRow(QStringLiteral("Número do preset"), presetNumber);
        for (const auto &entry : {std::pair<const char *, const char *>{"Ir ao preset", "preset_recall"},
                                 {"Guardar preset", "preset_save"}, {"Posição inicial", "home"}}) {
            auto *button = new QPushButton(QString::fromUtf8(entry.first), body);
            const QString action = QString::fromUtf8(entry.second);
            controlLayout->addRow(button);
            QObject::connect(button, &QPushButton::clicked, this, [this, action]() {
                manualTimer.stop(); send(QJsonObject{{"action", action}, {"number", presetNumber->value()}});
            });
        }
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
            useObsFrames = !obsSource->currentData().toString().isEmpty();
            const QString kind = protocol->currentData().toString();
            const bool invalidConnection = kind == "onvif" ? (ptz->text().isEmpty() || profile->text().isEmpty())
                : kind == "visca_serial" ? serialPort->text().isEmpty()
                : kind == "pelco_d" ? (host->text().isEmpty() && serialPort->text().isEmpty()) : host->text().isEmpty();
            if ((!useObsFrames && video->text().isEmpty()) || (!fixed && invalidConnection) || (fixed && !useObsFrames)) {
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
                             {"video", useObsFrames ? QStringLiteral("__obs_source__") : video->text()}, {"ptz", ptz->text()}, {"profile", profile->text()},
                             {"invertPan", invertPan->isChecked()}, {"invertTilt", invertTilt->isChecked()},
                             {"speed", speed->value()}, {"protocol", protocol->currentData().toString()},
                             {"preset", motionPreset->currentData().toString()}, {"host", host->text()},
                             {"port", port->value()}, {"serial", serialPort->text()}, {"baud", baud->value()},
                             {"address", address->value()}});
            watchdog.start(15000);
            if (useObsFrames) sourceTimer.start();
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
                if (trackingEnabled && message.contains("digitalCrop") && cameraMode->currentData().toString() == QStringLiteral("fixed")) {
                    const auto crop = message["digitalCrop"].toObject();
                    sceneZoom.apply(crop["left"].toDouble(), crop["top"].toDouble(), crop["width"].toDouble(), crop["height"].toDouble());
                }
                if (message.contains("frame")) {
                    preview->setFrame(QByteArray::fromBase64(message["frame"].toString().toLatin1()));
                    watchdog.start();
                }
            }
            if (pending.size() > 4000000) shutdown();
        });
        QObject::connect(&worker, &QProcess::readyReadStandardError, this, [this]() { worker.readAllStandardError(); });
        QObject::connect(&worker, &QProcess::finished, this, [this](int, QProcess::ExitStatus) { sourceTimer.stop(); sceneZoom.restore(); watchdog.stop(); manualTimer.stop(); });
        QObject::connect(stop, &QPushButton::clicked, this, [this]() { trackingEnabled = false; manualTimer.stop(); sceneZoom.restore(); send(QJsonObject{{"action", "stop"}}); });
        preview->selected = [this](QJsonArray box) { trackingEnabled = true; send(QJsonObject{{"action", "select"}, {"box", box}}); };
        QObject::connect(qApp, &QCoreApplication::aboutToQuit, this, [this]() { shutdown(); });
    }
    ~VisionTrackDock() override { shutdown(); }
};

