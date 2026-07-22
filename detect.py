import cv2
import numpy as np
import mediapipe as mp
from math import hypot

class LivenessDetector:

    def __init__(self):

        self.mp_face_mesh = mp.solutions.face_mesh

        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )

        self.blink_detected = False
        self.left_turn = False
        self.right_turn = False
        self.mouth_open = False

        self.live_score = 0

        self.blink_counter = 0
        self.left_turn_counter = 0
        self.right_turn_counter = 0
        self.mouth_open_counter = 0

        self.blink_history = []
        self.left_turn_history = []
        self.right_turn_history = []
        self.mouth_history = []
        self.max_history = 5

        self.prev_ear = 0.4

    def reset(self):
        self.blink_detected = False
        self.left_turn = False
        self.right_turn = False
        self.mouth_open = False
        self.live_score = 0
        self.blink_counter = 0
        self.left_turn_counter = 0
        self.right_turn_counter = 0
        self.mouth_open_counter = 0
        self.blink_history = []
        self.left_turn_history = []
        self.right_turn_history = []
        self.mouth_history = []
        self.prev_ear = 0.4

    def draw_corner_rect(self, img, pt1, pt2, color, thickness=2, d=15):
        x1, y1 = pt1
        x2, y2 = pt2

        cv2.line(img, (x1, y1), (x1 + d, y1), color, thickness)
        cv2.line(img, (x1, y1), (x1, y1 + d), color, thickness)

        cv2.line(img, (x2, y1), (x2 - d, y1), color, thickness)
        cv2.line(img, (x2, y1), (x2, y1 + d), color, thickness)

        cv2.line(img, (x1, y2), (x1 + d, y2), color, thickness)
        cv2.line(img, (x1, y2), (x1, y2 - d), color, thickness)

        cv2.line(img, (x2, y2), (x2 - d, y2), color, thickness)
        cv2.line(img, (x2, y2), (x2, y2 - d), color, thickness)

    # -----------------------
    # DISTANCE
    # -----------------------

    def distance(self, p1, p2):
        return hypot(
            p1[0] - p2[0],
            p1[1] - p2[1]
        )

    # -----------------------
    # EYE ASPECT RATIO
    # -----------------------

    def eye_ratio(self, eye_points):

        vertical1 = self.distance(eye_points[1], eye_points[5])
        vertical2 = self.distance(eye_points[2], eye_points[4])
        horizontal = self.distance(eye_points[0], eye_points[3])

        ratio = (vertical1 + vertical2) / (2.0 * horizontal)

        return ratio

    # -----------------------
    # BLINK DETECTION WITH DYNAMIC BASELINE
    # -----------------------

    def detect_blink_temporal(self, current_ear, threshold=0.20):
        """
        Accurate blink detection using dynamic personal baseline:
        - Computes each person's natural eye openness dynamically
        - Detects blink relative to their own baseline (handles small/large eyes)
        - Uses HIGH -> LOW -> HIGH temporal pattern
        """
        blink_occurred = False

        self.blink_history.append(current_ear)
        if len(self.blink_history) > self.max_history:
            self.blink_history.pop(0)

        if len(self.blink_history) >= 3:
            # Dynamic baseline: average of non-closed frames
            open_frames = [e for e in self.blink_history if e > threshold]
            dynamic_baseline = (
                sum(open_frames) / len(open_frames)
                if open_frames else threshold + 0.05
            )

            # Blink relative to person's own baseline
            if (self.blink_history[-3] > dynamic_baseline * 0.85 and
                self.blink_history[-2] < dynamic_baseline * 0.65 and
                current_ear > dynamic_baseline * 0.80):
                blink_occurred = True

        if blink_occurred:
            self.blink_counter = 5

        if self.blink_counter > 0:
            self.blink_counter -= 1

        self.prev_ear = current_ear
        return self.blink_counter > 0

    # -----------------------
    # PROCESS
    # -----------------------

    def process(self, frame):

        h, w, _ = frame.shape

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = self.face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return frame, 0, 100

        face = results.multi_face_landmarks[0]

        points = []

        for lm in face.landmark:
            x = int(lm.x * w)
            y = int(lm.y * h)
            points.append((x, y))

        # -----------------------
        # FACE BOUNDS (computed early for ratio calculations)
        # -----------------------

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]

        x_min = min(xs)
        y_min = min(ys)
        x_max = max(xs)
        y_max = max(ys)

        face_height = y_max - y_min

        # -----------------------
        # LEFT EYE
        # -----------------------

        left_eye = [
            points[33],
            points[160],
            points[158],
            points[133],
            points[153],
            points[144]
        ]

        left_ratio = self.eye_ratio(left_eye)

        # -----------------------
        # RIGHT EYE
        # -----------------------

        right_eye = [
            points[362],
            points[385],
            points[387],
            points[263],
            points[373],
            points[380]
        ]

        right_ratio = self.eye_ratio(right_eye)

        ear = (left_ratio + right_ratio) / 2.0

        # -----------------------
        # BLINK DETECTION (DYNAMIC BASELINE)
        # -----------------------

        self.blink_detected = self.detect_blink_temporal(ear, threshold=0.20)

        # -----------------------
        # HEAD POSE (RATIO-BASED, DISTANCE-INDEPENDENT)
        # -----------------------

        nose = points[1]
        left_face = points[234][0]
        right_face = points[454][0]
        face_width = right_face - left_face
        face_center = (left_face + right_face) // 2

        offset = nose[0] - face_center

        # Normalize offset by face width (works at any camera distance)
        offset_ratio = offset / face_width if face_width > 0 else 0

        # 0.07 = nose shifted 7% of face width
        if offset_ratio < -0.07:
            self.left_turn_counter += 1
        else:
            self.left_turn_counter = max(0, self.left_turn_counter - 1)

        if offset_ratio > 0.07:
            self.right_turn_counter += 1
        else:
            self.right_turn_counter = max(0, self.right_turn_counter - 1)

        self.left_turn = self.left_turn_counter >= 1
        self.right_turn = self.right_turn_counter >= 1

        # -----------------------
        # MOUTH OPEN DETECTION (RATIO-BASED, DISTANCE-INDEPENDENT)
        # -----------------------

        upper_lip = points[13]
        lower_lip = points[14]

        mouth_gap = self.distance(upper_lip, lower_lip)

        # Normalize mouth gap by face height (distance-independent)
        mouth_ratio = mouth_gap / face_height if face_height > 0 else 0

        # 4% of face height is a reliable open-mouth threshold
        if mouth_ratio > 0.04:
            self.mouth_open_counter += 1
        else:
            self.mouth_open_counter = max(0, self.mouth_open_counter - 1)

        self.mouth_open = self.mouth_open_counter >= 1

        # -----------------------
        # LIVE SCORE
        # -----------------------

        score = 0

        if self.blink_detected:
            score += 25

        if self.left_turn:
            score += 25

        if self.right_turn:
            score += 25

        if self.mouth_open:
            score += 25

        self.live_score = score

        spoof_score = 100 - score

        # -----------------------
        # BOX COLOR & OVERLAYS
        # -----------------------

        color = (
            (0, 255, 0)
            if score >= 50
            else (0, 0, 255)
        )

        cv2.rectangle(
            frame,
            (x_min, y_min),
            (x_max, y_max),
            color,
            3
        )

        # Draw cybernetic scanning face mesh dots
        for pt in points:
            cv2.circle(frame, pt, 1, (255, 255, 0), -1)

        # -----------------------
        # STATUS INDICATORS
        # -----------------------

        cv2.putText(
            frame,
            f"Blink: {'YES' if self.blink_detected else 'NO'}",
            (20, 420),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            f"Left Turn: {'YES' if self.left_turn else 'NO'}",
            (20, 455),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            f"Right Turn: {'YES' if self.right_turn else 'NO'}",
            (20, 490),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            f"Mouth Open: {'YES' if self.mouth_open else 'NO'}",
            (20, 525),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        return frame, score, spoof_score

    # -----------------------
    # DRAW UI
    # -----------------------

    def draw_ui(self, frame, live, spoof):

        label = (
            "LIVE"
            if live >= 50
            else "SPOOF"
        )

        color = (
            (0, 255, 0)
            if live >= 50
            else (0, 0, 255)
        )

        cv2.putText(
            frame,
            label,
            (150, 250),
            cv2.FONT_HERSHEY_SIMPLEX,
            2,
            color,
            4
        )

        cv2.putText(
            frame,
            f"LIVE: {live}%",
            (150, 300),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            f"SPOOF: {spoof}%",
            (150, 340),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2
        )

        return frame
