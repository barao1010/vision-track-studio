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
from ptz_companion import OnvifPTZ, tracker_factory
from ptz_target_controller import Box, TargetPTZController
from ai_detector import PersonDetector, distinct_match


def emit(**data):
    print(json.dumps(data), flush=True)


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
    tracker = reference = None
    try:
        config = commands.get(timeout=15)
        emit(status="A carregar o detector de pessoas por IA…")
        detector = PersonDetector()
        camera = OnvifPTZ(config["ptz"], config["profile"], os.environ["VTS_PTZ_USER"],
                          os.environ["VTS_PTZ_PASSWORD"], invert_pan=config.get("invertPan", False),
                          invert_tilt=config.get("invertTilt", True))
        controller = TargetPTZController(camera, max_speed=max(.05, min(.5, float(config.get("speed", .15)))))
        stream = cv2.VideoCapture(config["video"], cv2.CAP_FFMPEG,
                                 [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 4000,
                                  cv2.CAP_PROP_READ_TIMEOUT_MSEC, 1000])
        if not stream.isOpened():
            raise RuntimeError("Não foi possível abrir o vídeo da câmera.")
        emit(status="Ligado. Arraste um retângulo sobre a pessoa.")
        frame_number = 0
        while True:
            ok, frame = stream.read()
            if not ok:
                controller.stop()
                emit(status="Vídeo interrompido. Câmera parada.")
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
                    tracker = reference = None
                    emit(status="Rastreio parado.")
                elif action == "select":
                    controller.stop()
                    tracker = reference = None
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
                    tracker = tracker_factory()
                    tracker.init(frame, (x, y, bw, bh))
                    reference = histogram(frame[y:y + bh, x:x + bw])
                    controller.select(1)
                    emit(status="Alvo selecionado. Rastreio ativo.")
            if tracker is not None:
                found, box = tracker.update(frame)
                x, y, bw, bh = [int(v) for v in box]
                crop = frame[max(0, y):min(h, y + bh), max(0, x):min(w, x + bw)]
                if found and frame_number % 3 == 0:
                    found = distinct_match((x, y, bw, bh), detector.detect(frame)) is not None
                if found and crop.size and cv2.compareHist(reference, histogram(crop), cv2.HISTCMP_BHATTACHARYYA) < .55:
                    controller.update(w, h, {1: Box(x, y, bw, bh)})
                    cv2.rectangle(frame, (x, y), (x + bw, y + bh), (0, 220, 0), 2)
                else:
                    controller.stop()
                    tracker = reference = None
                    emit(status="Alvo perdido ou aparência ambígua. Selecione novamente.")
            encoded, image = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
            if encoded:
                emit(frame=base64.b64encode(image).decode("ascii"))
            time.sleep(.05)
    except Exception:
        # Never echo RTSP URLs, passwords or HTTP exception bodies into logs.
        emit(status="Falha na ligação ou no rastreio. Verifique vídeo, ONVIF e credenciais.")
        sys.exit(1)
    finally:
        if camera is not None:
            try:
                camera.stop()
            except Exception:
                pass
        if stream is not None:
            stream.release()


def histogram(crop):
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    value = cv2.calcHist([hsv], [0, 1], None, [24, 24], [0, 180, 0, 256])
    return cv2.normalize(value, value)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        assert PersonDetector().detect(np.zeros((360, 640, 3), dtype=np.uint8)) == []
        emit(status="Packaged AI model and runtime verified.")
    else:
        main()
