"""GPL-2.0-or-later. JSON-line worker for the native Vision Track Studio dock."""
import base64
import json
import os
import queue
import sys
import threading
import time

import cv2
import numpy as np
from protocol_drivers import create_camera
from identity_tracker import IdentityTracker
from cinema_controller import CinemaPTZController
from ptz_target_controller import Box, TargetPTZController
from ai_detector import PersonDetector, distinct_match
from digital_zoom import DigitalZoomController


def emit(**data):
    print(json.dumps(data), flush=True)


class FixedCamera:
    """Virtual control surface: fixed cameras cannot receive pan/tilt commands."""
    def move(self, *args):
        pass
    def stop(self):
        pass
    def home(self):
        pass
    def preset(self, *args):
        pass


def open_video(video):
    # Video capture cards and USB webcams are exposed by Windows as indexes.
    if isinstance(video, int) or (isinstance(video, str) and video.startswith("device:")):
        index = int(video.split(":", 1)[1]) if isinstance(video, str) else video
        return cv2.VideoCapture(index, cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY)
    return cv2.VideoCapture(video, cv2.CAP_FFMPEG,
                            [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 4000,
                             cv2.CAP_PROP_READ_TIMEOUT_MSEC, 1000])


def main():
    commands = queue.Queue()

    def read_commands():
        for line in sys.stdin:
            try:
                commands.put(json.loads(line))
            except (ValueError, TypeError):
                commands.put({"action": "stop"})
        commands.put({"action": "quit"})

    threading.Thread(target=read_commands, daemon=True).start()
    camera = stream = controller = None
    identity = IdentityTracker()
    digital = DigitalZoomController()
    fixed_mode = False
    manual = None
    manual_until = 0
    try:
        config = commands.get(timeout=15)
        emit(status="A carregar o detector de pessoas por IA…")
        detector = PersonDetector()
        fixed_mode = config.get("cameraMode") == "fixed"
        camera = FixedCamera() if fixed_mode else create_camera(config, os.environ.get("VTS_PTZ_USER", ""), os.environ.get("VTS_PTZ_PASSWORD", ""))
        controller = CinemaPTZController(camera, preset=config.get("preset", "cinema"),
                                         max_speed=max(.05, min(.6, float(config.get("speed", .32)))))
        stream = open_video(config["video"])
        if not stream.isOpened():
            raise RuntimeError("Não foi possível abrir o vídeo da câmera.")
        emit(status="Ligado. Arraste um retângulo sobre a pessoa.")
        frame_number = 0
        while True:
            ok, frame = stream.read()
            if not ok:
                controller.stop()
                emit(status="Vídeo interrompido. Câmera parada.")
                if fixed_mode:
                    emit(zoomReset=True)
                break
            h, w = frame.shape[:2]
            frame_number += 1
            frame = cv2.resize(frame, (640, max(1, int(640 * h / w))))
            h, w = frame.shape[:2]
            while not commands.empty():
                command = commands.get_nowait()
                action = command.get("action")
                if action == "quit":
                    return
                if action == "stop":
                    controller.stop()
                    digital.reset()
                    if fixed_mode:
                        emit(zoomReset=True)
                    identity.clear()
                    manual = None
                    emit(status="Rastreio parado.")
                elif action == "select":
                    controller.stop()
                    digital.reset()
                    if fixed_mode:
                        emit(zoomReset=True)
                    identity.clear()
                    manual = None
                    x, y, bw, bh = [int(v) for v in command["box"]]
                    x, y = max(0, min(x, w - 1)), max(0, min(y, h - 1))
                    bw, bh = min(bw, w - x), min(bh, h - y)
                    if bw < 24 or bh < 24:
                        emit(status="Selecione uma área maior sobre o corpo da pessoa.")
                        continue
                    matched = distinct_match((x, y, bw, bh), detector.detect(frame))
                    if matched is None:
                        emit(status="A IA não encontrou uma pessoa distinta nessa área. Selecione novamente.")
                        continue
                    x, y, bw, bh = matched
                    identity.select((x, y, bw, bh), appearance(frame, (x, y, bw, bh)), time.monotonic())
                    emit(status="Alvo selecionado. Rastreio ativo.")
                elif action == "manual":
                    if fixed_mode:
                        emit(status="Câmara fixa: acompanhamento disponível através do zoom digital.")
                        continue
                    identity.clear()
                    if manual is None:
                        controller.stop()
                    manual = tuple(max(-1, min(1, float(command.get(axis, 0)))) for axis in ("pan", "tilt", "zoom"))
                    manual_until = time.monotonic() + .3
                elif action in ("preset_recall", "preset_save", "home"):
                    if fixed_mode:
                        emit(status="Presets físicos indisponíveis em câmaras fixas.")
                        continue
                    identity.clear()
                    manual = None
                    controller.stop()
                    if action == "home":
                        camera.home()
                    else:
                        camera.preset(int(command.get("number", 1)), action == "preset_save")
                    emit(status="Comando PTZ enviado.")
            now = time.monotonic()
            if manual is not None:
                if now < manual_until:
                    camera.move(*manual)
                else:
                    controller.stop()
                    manual = None
            elif identity.box is not None:
                people = detector.detect(frame)
                signatures = [appearance(frame, box) for box in people]
                old_state = identity.state
                box = identity.update(people, signatures, now, frame_number)
                if box is not None:
                    if fixed_mode:
                        crop = digital.update(w, h, box, identity.velocity)
                        if crop is not None:
                            emit(digitalCrop=crop)
                    else:
                        controller.update(w, h, box, identity.velocity, now)
                    x, y, bw, bh = [int(v) for v in box]
                    cv2.rectangle(frame, (x, y), (x + bw, y + bh), (0, 220, 0), 2)
                else:
                    if controller.active or old_state == "locked":
                        controller.stop()
                if identity.state != old_state:
                    messages = {
                        "locked": "Alvo original confirmado. Rastreio retomado.",
                        "lost": "Alvo temporariamente perdido. Câmera parada; seleção preservada.",
                        "ambiguous": "Pessoas próximas ou semelhantes. Câmera parada; alvo original preservado.",
                        "recovering": "A confirmar o alvo original em vários quadros…",
                    }
                    emit(status=messages.get(identity.state, identity.state))
            encoded, image = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
            if encoded:
                emit(frame=base64.b64encode(image).decode("ascii"))
            time.sleep(.05)
    except Exception:
        # Never echo RTSP URLs, passwords or HTTP exception bodies into logs.
        emit(status="Falha na ligação ou no rastreio. Verifique vídeo, ONVIF e credenciais.")
        sys.exit(1)
    finally:
        if fixed_mode:
            emit(zoomReset=True)
        if camera is not None:
            try:
                camera.stop()
            except Exception:
                pass
        if camera is not None and hasattr(camera, "close"):
            try:
                camera.close()
            except Exception:
                pass
        if stream is not None:
            stream.release()


def appearance(frame, box):
    x, y, w, h = box
    left, top = max(0, int(x+w/6)), max(0, int(y+h/6))
    right, bottom = min(frame.shape[1], int(x+w*5/6)), min(frame.shape[0], int(y+h*2/3))
    crop = frame[top:bottom, left:right]
    if crop.size == 0:
        return [0.] * 27
    rgb = cv2.cvtColor(cv2.resize(crop, (6, 6)), cv2.COLOR_BGR2RGB)
    return (rgb.reshape(-1, 3)[::4].reshape(-1) / 255.).tolist()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        assert PersonDetector().detect(np.zeros((360, 640, 3), dtype=np.uint8)) == []
        emit(status="Packaged AI model and runtime verified.")
    else:
        main()

