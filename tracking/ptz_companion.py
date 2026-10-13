#!/usr/bin/env python3
"""Vision Track Studio: experimental selectable-person PTZ tracker.

Standalone companion while native OBS Qt integration is being developed.
Only connect to cameras you own or are authorized to control.
"""
import argparse
import os
import time
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import cv2
import requests
from requests.auth import HTTPDigestAuth

from ptz_target_controller import Box, TargetPTZController

SOAP = "http://www.w3.org/2003/05/soap-envelope"
PTZ = "http://www.onvif.org/ver20/ptz/wsdl"

class OnvifPTZ:
    def __init__(self, url, profile, username, password, timeout=3):
        if not url.startswith(("http://", "https://")):
            raise ValueError("PTZ endpoint must be HTTP(S)")
        if not profile:
            raise ValueError("ONVIF profile token is required")
        self.url, self.profile, self.timeout = url, profile, timeout
        self.http = requests.Session()
        self.http.auth = HTTPDigestAuth(username, password)
        self.http.headers["Content-Type"] = "application/soap+xml; charset=utf-8"
        self.stop()

    def send(self, action, payload):
        env = ET.Element(f"{{{SOAP}}}Envelope")
        body = ET.SubElement(env, f"{{{SOAP}}}Body")
        node = ET.SubElement(body, f"{{{PTZ}}}{action}")
        ET.SubElement(node, f"{{{PTZ}}}ProfileToken").text = self.profile
        payload(node)
        data = ET.tostring(env, encoding="utf-8", xml_declaration=True)
        r = self.http.post(self.url, data=data, timeout=self.timeout)
        r.raise_for_status()
        try:
            root = ET.fromstring(r.content)
            if root.find(f".//{{{SOAP}}}Fault") is not None:
                raise RuntimeError("ONVIF camera returned SOAP Fault")
        except ET.ParseError as exc:
            raise RuntimeError("Invalid ONVIF XML response") from exc

    def move(self, pan, tilt, zoom):
        def content(node):
            v = ET.SubElement(node, f"{{{PTZ}}}Velocity")
            xy = ET.SubElement(v, "{http://www.onvif.org/ver10/schema}PanTilt")
            xy.set("x", str(round(max(-1, min(1, pan)), 4)))
            xy.set("y", str(round(max(-1, min(1, tilt)), 4)))
            z = ET.SubElement(v, "{http://www.onvif.org/ver10/schema}Zoom")
            z.set("x", str(round(max(-1, min(1, zoom)), 4)))
        self.send("ContinuousMove", content)

    def stop(self):
        def content(node):
            ET.SubElement(node, f"{{{PTZ}}}PanTilt").text = "true"
            ET.SubElement(node, f"{{{PTZ}}}Zoom").text = "true"
        self.send("Stop", content)

def tracker_factory():
    legacy = getattr(cv2, "legacy", None)
    if legacy and hasattr(legacy, "TrackerCSRT_create"):
        return legacy.TrackerCSRT_create()
    if hasattr(cv2, "TrackerCSRT_create"):
        return cv2.TrackerCSRT_create()
    raise RuntimeError("Install opencv-contrib-python (CSRT tracker is unavailable)")

def main():
    parser = argparse.ArgumentParser(description="Vision Track Studio PTZ companion (experimental)")
    parser.add_argument("--rtsp", required=True, help="RTSP video URL")
    parser.add_argument("--ptz-url", required=True, help="ONVIF PTZ endpoint URL")
    parser.add_argument("--profile-token", required=True, help="ONVIF media profile token")
    parser.add_argument("--username", default=os.getenv("VTS_PTZ_USER", ""))
    parser.add_argument("--invert-pan", action="store_true")
    parser.add_argument("--invert-tilt", action="store_true")
    args = parser.parse_args()
    password = os.environ.get("VTS_PTZ_PASSWORD")
    if not args.username or password is None:
        parser.error("Set VTS_PTZ_USER and VTS_PTZ_PASSWORD environment variables")
    camera = OnvifPTZ(args.ptz_url, args.profile_token, args.username, password)
    stream = cv2.VideoCapture(args.rtsp)
    if not stream.isOpened():
        camera.stop()
        raise RuntimeError("Cannot open RTSP stream")
    ctl = TargetPTZController(camera)
    selected_tracker = None
    selection = [None, None]
    title = "Vision Track Studio - PTZ tracking (ESC: exit, S: stop)"

    def mouse(event, x, y, flags, userdata):
        nonlocal selected_tracker
        if event == cv2.EVENT_LBUTTONDOWN:
            selection[0] = (x, y)
            selection[1] = None
        elif event == cv2.EVENT_LBUTTONUP and selection[0] is not None:
            selection[1] = (x, y)
    cv2.namedWindow(title)
    cv2.setMouseCallback(title, mouse)
    failure_count = 0
    try:
        while True:
            ok, frame = stream.read()
            if not ok:
                failure_count += 1
                if failure_count >= 8:
                    break
                time.sleep(0.1)
                continue
            failure_count = 0
            h, w = frame.shape[:2]
            if selection[0] is not None and selection[1] is not None:
                x0, y0 = selection[0]
                x1, y1 = selection[1]
                left, top = min(x0, x1), min(y0, y1)
                width, height = abs(x1 - x0), abs(y1 - y0)
                selection[:] = [None, None]
                if width >= 24 and height >= 24:
                    ctl.stop()
                    selected_tracker = tracker_factory()
                    selected_tracker.init(frame, (left, top, width, height))
                    ctl.select(1)
            if selected_tracker is not None:
                found, (x, y, bw, bh) = selected_tracker.update(frame)
                if found:
                    ctl.update(w, h, {1: Box(x, y, bw, bh)})
                    cv2.rectangle(frame, (int(x), int(y)), (int(x+bw), int(y+bh)), (0, 220, 0), 2)
                else:
                    ctl.update(w, h, {})
            cv2.putText(frame, "Drag around person | S stop | ESC exit", (12, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, .6, (255, 255, 255), 2)
            cv2.imshow(title, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                break
            if key in (ord("s"), ord("S")):
                ctl.stop()
                selected_tracker = None
    finally:
        try:
            ctl.stop()
        finally:
            stream.release()
            cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
