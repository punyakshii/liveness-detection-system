import cv2
import numpy as np
import time

class LivenessDetector:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml')
        self.smile_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_smile.xml')

        self.reset_state()
        self.prev_face_center = None
        self.face_missing_frames = 0

    def reset_state(self):
        self.eye_blinked = False
        self.head_moved = False
        self.mouth_moved = False
        self.prev_eyes_open = True
        self.prev_mouth_open = False
        self.last_blink_time = 0
        self.face_rect = None
        self.start_time = time.time()

    def detect_face(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, 1.1, 5, minSize=(80, 80))

        if len(faces) == 0:
            self.face_rect = None
            return False

        self.face_rect = max(faces, key=lambda r: r[2]*r[3])
        return True

    def detect_eye_blink(self, frame):
        if self.face_rect is None:
            return

        x, y, w, h = self.face_rect
        roi = cv2.cvtColor(frame[y:y+h, x:x+w], cv2.COLOR_BGR2GRAY)

        eyes = self.eye_cascade.detectMultiScale(
            roi[0:h//2, :], 1.05, 3, minSize=(15, 15))

        eyes_open = len(eyes) >= 2
        now = time.time()

        if self.prev_eyes_open and not eyes_open:
            self.last_blink_time = now

        if not self.prev_eyes_open and eyes_open:
            if 0.1 < now - self.last_blink_time < 0.7:
                self.eye_blinked = True
                print("Blink detected")  # safe instead of winsound

        self.prev_eyes_open = eyes_open

    def detect_head_movement(self):
        if self.face_rect is None:
            return

        x, y, w, h = self.face_rect
        center = np.array([x + w//2, y + h//2])

        if self.prev_face_center is not None:
            dist = np.linalg.norm(center - self.prev_face_center)
            if dist > 20:
                self.head_moved = True

        self.prev_face_center = center

    def detect_mouth_movement(self, frame):
        if self.face_rect is None:
            return

        x, y, w, h = self.face_rect
        roi = cv2.cvtColor(frame[y:y+h, x:x+w], cv2.COLOR_BGR2GRAY)

        mouths = self.smile_cascade.detectMultiScale(
            roi[int(h*0.6):h, :], 1.3, 15, minSize=(30, 20))

        mouth_open = len(mouths) > 0

        if self.prev_mouth_open and not mouth_open:
            self.mouth_moved = True

        self.prev_mouth_open = mouth_open

    def calculate_percentages(self):
        cues = sum([self.eye_blinked, self.head_moved, self.mouth_moved])
        live_percent = int((cues / 3) * 100)
        spoof_percent = 100 - live_percent
        return live_percent, spoof_percent

    def process(self, frame):
        face_found = self.detect_face(frame)

        if not face_found:
            self.face_missing_frames += 1
            if self.face_missing_frames > 10:
                self.reset_state()
            return frame

        self.face_missing_frames = 0

        self.detect_eye_blink(frame)
        self.detect_head_movement()
        self.detect_mouth_movement(frame)

        return frame

    def draw_ui(self, frame):
        h, w = frame.shape[:2]

        if self.face_rect is not None:
            x, y, fw, fh = self.face_rect
            cv2.rectangle(frame, (x, y), (x+fw, y+fh), (255, 0, 0), 2)

        live_p, spoof_p = self.calculate_percentages()

        if live_p >= 66:
            label = "LIVE"
            color = (0, 255, 0)
        else:
            label = "SPOOF"
            color = (0, 0, 255)

        cv2.putText(frame, label, (w//2 - 150, h//2),
                    cv2.FONT_HERSHEY_SIMPLEX, 2.5, color, 6)

        return frame
