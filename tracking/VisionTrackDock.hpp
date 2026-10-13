// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <QApplication>
#include <QCheckBox>
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
    QLineEdit *video, *ptz, *profile, *user, *password;
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
        watchdog.stop();
        send(QJsonObject{{"action", "quit"}});
        if (!worker.waitForFinished(2500)) {
            worker.kill();
            worker.waitForFinished(500);
        }
    }
public:
    explicit VisionTrackDock(QMainWindow *main) : QDockWidget(QStringLiteral("Vision Track • Rastreio PTZ"), main) {
        setObjectName(QStringLiteral("visionTrackDock"));
        auto *body = new QWidget(this);
        auto *layout = new QFormLayout(body);
        video = new QLineEdit(body); video->setPlaceholderText(QStringLiteral("rtsp://câmera/stream"));
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
        layout->addRow(invertPan); layout->addRow(invertTilt);
        speed = new QDoubleSpinBox(body); speed->setRange(.05, .5); speed->setSingleStep(.05); speed->setValue(.15);
        layout->addRow(QStringLiteral("Velocidade máxima"), speed);
        connectButton = new QPushButton(QStringLiteral("Ligar / desligar câmera"), body);
        layout->addRow(connectButton);
        preview = new VTPreview(body); layout->addRow(preview);
        auto *stop = new QPushButton(QStringLiteral("PARAR RASTREIO"), body); layout->addRow(stop);
        status = new QLabel(QStringLiteral("Pronto. Credenciais guardadas apenas nesta sessão."), body);
        status->setWordWrap(true); layout->addRow(status);
        setWidget(body);
        worker.setProcessChannelMode(QProcess::SeparateChannels);
        watchdog.setInterval(4000);
        watchdog.setSingleShot(true);
        QObject::connect(&watchdog, &QTimer::timeout, this, [this]() {
            shutdown(); status->setText(QStringLiteral("Sem resposta do rastreio. Ligação encerrada."));
        });
        QObject::connect(connectButton, &QPushButton::clicked, this, [this]() {
            if (worker.state() != QProcess::NotRunning) { shutdown(); return; }
            if (video->text().isEmpty() || ptz->text().isEmpty() || profile->text().isEmpty() || user->text().isEmpty()) {
                status->setText(QStringLiteral("Preencha vídeo, serviço ONVIF, perfil e utilizador.")); return;
            }
            pending.clear();
            auto env = QProcessEnvironment::systemEnvironment();
            env.insert("VTS_PTZ_USER", user->text()); env.insert("VTS_PTZ_PASSWORD", password->text());
            worker.setProcessEnvironment(env);
            worker.setProgram(QApplication::applicationDirPath() + "/vision-track-worker/vision-track-worker.exe");
            status->setText(QStringLiteral("A ligar à câmera…"));
            worker.start();
        });
        QObject::connect(&worker, &QProcess::started, this, [this]() {
            send(QJsonObject{{"video", video->text()}, {"ptz", ptz->text()}, {"profile", profile->text()},
                             {"invertPan", invertPan->isChecked()}, {"invertTilt", invertTilt->isChecked()},
                             {"speed", speed->value()}});
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
                if (message.contains("frame")) {
                    preview->setFrame(QByteArray::fromBase64(message["frame"].toString().toLatin1()));
                    watchdog.start();
                }
            }
            if (pending.size() > 4000000) shutdown();
        });
        QObject::connect(&worker, &QProcess::readyReadStandardError, this, [this]() { worker.readAllStandardError(); });
        QObject::connect(&worker, &QProcess::finished, this, [this](int, QProcess::ExitStatus) { watchdog.stop(); });
        QObject::connect(stop, &QPushButton::clicked, this, [this]() { send(QJsonObject{{"action", "stop"}}); });
        preview->selected = [this](QJsonArray box) { send(QJsonObject{{"action", "select"}, {"box", box}}); };
        QObject::connect(qApp, &QCoreApplication::aboutToQuit, this, [this]() { shutdown(); });
    }
    ~VisionTrackDock() override { shutdown(); }
};
