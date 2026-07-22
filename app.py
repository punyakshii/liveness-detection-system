from flask import Flask, render_template, Response, redirect, url_for
from flask import session, request

import cv2
import mediapipe as mp
import threading
import time
import json
import queue
import sounddevice as sd
sd.default.samplerate = 16000
sd.default.channels = 1

from vosk import Model, KaldiRecognizer
from deepface import DeepFace
from detect import LivenessDetector

# ==========================
# FLASK
# ==========================

app = Flask(__name__)
app.secret_key = "secret123"

USERNAME = "punyakshi"
PASSWORD = "solanki1234"

# ==========================
# CAMERA
# ==========================

camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

camera.set(cv2.CAP_PROP_BRIGHTNESS, 150)
camera.set(cv2.CAP_PROP_CONTRAST, 150)
camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

if not camera.isOpened():
    print("Camera Error")

# ==========================
# LIVENESS
# ==========================

detector = LivenessDetector()

# ==========================
# MEDIAPIPE FACE DETECTION
# ==========================

mp_face = mp.solutions.face_detection

face_detector = mp_face.FaceDetection(
    model_selection=1,
    min_detection_confidence=0.85
)

# ==========================
# VOSK
# ==========================

MODEL_PATH = "vosk-model-small-en-us-0.15"

vosk_model = Model(MODEL_PATH)

recognizer = KaldiRecognizer(
    vosk_model,
    16000
)

audio_queue = queue.Queue()

voice_text = "..."
voice_status = "Idle"

# ==========================
# EMOTION
# ==========================

emotion = "Neutral"
emotion_buffer = []
emotion_confidence = 0

# ==========================
# AUDIO CALLBACK
# ==========================

def audio_callback(indata, frames, time_info, status):

    if status:
        return

    audio_queue.put(bytes(indata))

# ==========================
# VOICE THREAD
# ==========================

def voice_worker():

    global voice_text
    global voice_status

    stream = sd.RawInputStream(
        samplerate=16000,
        blocksize=8000,
        dtype='int16',
        channels=1,
        callback=audio_callback
    )

    stream.start()

    while True:

        try:

            data = audio_queue.get()

            if recognizer.AcceptWaveform(data):

                result = json.loads(
                    recognizer.Result()
                )

                text = result.get("text", "")

                if text.strip() != "":
                    voice_text = text

            voice_status = "Listening"

        except:
            voice_status = "Error"

# ==========================
# START VOICE THREAD
# ==========================

threading.Thread(
    target=voice_worker,
    daemon=True
).start()
# ==========================
# VIDEO STREAM
# ==========================

def generate_frames():

    global emotion
    global emotion_buffer
    global emotion_confidence
    global voice_text
    global voice_status

    frame_counter = 0

    while True:

        success, frame = camera.read()

        if not success:
            continue

        frame = cv2.flip(frame, 1)

        # Keep a clean copy of the frame for face cropping and emotion detection
        clean_frame = frame.copy()

        # ==========================
        # LIVENESS DETECTION
        # ==========================

        frame, live, spoof = detector.process(frame)
        frame = detector.draw_ui(frame, live, spoof)

        # ==========================
        # FACE DETECTION (Using clean copy to prevent landmark interference)
        # ==========================

        clean_rgb = cv2.cvtColor(
            clean_frame,
            cv2.COLOR_BGR2RGB
        )

        results = face_detector.process(clean_rgb)

        if results.detections:

            for detection in results.detections:

                bbox = detection.location_data.relative_bounding_box

                h, w, _ = frame.shape

                x = max(
                    int(bbox.xmin * w),
                    0
                )

                y = max(
                    int(bbox.ymin * h),
                    0
                )

                fw = int(bbox.width * w)
                fh = int(bbox.height * h)

                # Redundant rectangle drawing removed to keep liveness target brackets clean.

                frame_counter += 1

                # ==========================
                # EMOTION DETECTION (Crop from clean copy)
                # ==========================

                if frame_counter % 15 == 0:

                    try:

                        # 35% padding — forehead, jaw, cheeks fully in frame
                        pad_x = int(fw * 0.35)
                        pad_y = int(fh * 0.35)

                        x1 = max(x - pad_x, 0)
                        y1 = max(y - pad_y, 0)
                        x2 = min(x + fw + pad_x, clean_frame.shape[1])
                        y2 = min(y + fh + pad_y, clean_frame.shape[0])

                        face_crop = clean_frame[y1:y2, x1:x2]

                        if face_crop.size == 0 or face_crop.shape[0] < 48 or face_crop.shape[1] < 48:
                            raise ValueError("Face crop too small")

                        # Resize maintaining aspect ratio then letterbox to
                        # 224x224 — squishing distorts muscle shape and causes
                        # happy to be misclassified as fear.
                        h_c, w_c = face_crop.shape[:2]
                        scale = 224 / max(h_c, w_c)
                        nw, nh = int(w_c * scale), int(h_c * scale)
                        resized = cv2.resize(face_crop, (nw, nh), interpolation=cv2.INTER_LINEAR)
                        canvas = cv2.copyMakeBorder(
                            resized,
                            (224 - nh) // 2, (224 - nh + 1) // 2,
                            (224 - nw) // 2, (224 - nw + 1) // 2,
                            cv2.BORDER_CONSTANT, value=(0, 0, 0)
                        )

                        result = DeepFace.analyze(
                            canvas,
                            actions=['emotion'],
                            detector_backend='skip',
                            enforce_detection=False,
                            silent=True
                        )

                        raw_scores = result[0]['emotion']

                        # === PER-EMOTION CALIBRATION ===
                        # Weights derived from fer2013 class imbalance and
                        # known confusion patterns (fear ↔ happy, neutral bias).
                        # Happy gets the biggest boost — it's the most naturally
                        # expressed emotion and the most commonly misclassified.
                        calibration = {
                            'happy':    2.0,   # strongly boost — most natural
                            'surprise': 1.6,   # clearly distinct (raised brows)
                            'sad':      1.3,   # downturned mouth is distinctive
                            'angry':    1.3,   # furrowed brows are distinctive
                            'disgust':  1.0,   # neutral weight
                            'fear':     0.5,   # discount — often confused w/ happy
                            'neutral':  0.45,  # heavy discount for dataset bias
                        }

                        adjusted = {
                            label: score * calibration.get(label, 1.0)
                            for label, score in raw_scores.items()
                        }

                        dominant = max(adjusted, key=adjusted.get)

                        # Clean display labels
                        label_map = {
                            'happy':    'Happy',
                            'sad':      'Sad',
                            'angry':    'Angry',
                            'surprise': 'Surprised',
                            'fear':     'Fear',
                            'disgust':  'Disgust',
                            'neutral':  'Neutral',
                        }
                        dominant = label_map.get(dominant, dominant.capitalize())

                        emotion_buffer.append(dominant)

                        # Buffer of 3 — catches expressions within ~0.5 sec
                        if len(emotion_buffer) > 3:
                            emotion_buffer.pop(0)

                        emotion = max(
                            set(emotion_buffer),
                            key=emotion_buffer.count
                        )

                    except:
                        pass



        # ==========================
        # DASHBOARD PANEL
        # ==========================

        overlay = frame.copy()

        cv2.rectangle(
            overlay,
            (10, 10),
            (430, 140),
            (20, 20, 20),
            -1
        )

        cv2.addWeighted(
            overlay,
            0.7,
            frame,
            0.3,
            0,
            frame
        )

        cv2.putText(
            frame,
            f"Emotion: {emotion}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255,255,255),
            2
        )

        cv2.putText(
            frame,
            f"Voice: {voice_text[:30]}",
            (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255,255,255),
            2
        )

        cv2.putText(
            frame,
            f"Status: {voice_status}",
            (20,110),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0,255,255),
            2
        )

        # ==========================
        # ENCODE FRAME
        # ==========================

        ret, buffer = cv2.imencode(
            '.jpg',
            frame
        )

        frame_bytes = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n'
            + frame_bytes +
            b'\r\n'
        )

        time.sleep(0.03)

# ==========================
# LOGIN
# ==========================

@app.route(
    '/login',
    methods=['GET', 'POST']
)
def login():

    error = ""

    if request.method == 'POST':

        username = request.form.get(
            'username'
        )

        password = request.form.get(
            'password'
        )

        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if (
            username == USERNAME and
            password == PASSWORD
        ):
            # Enforce biometric check for professional security
            if detector.live_score >= 50:
                session['user'] = username
                if is_ajax:
                    return {"success": True, "redirect": "/"}
                return redirect(
                    url_for('index')
                )
            else:
                error = "Biometric Verification Required. Please complete gestures."
                if is_ajax:
                    return {"success": False, "error": error}

        else:
            error = "Invalid Credentials"
            if is_ajax:
                return {"success": False, "error": error}

    return render_template(
        'login.html',
        error=error
    )


# ==========================
# HOME
# ==========================

@app.route('/')
def index():

    if 'user' not in session:
        return redirect(
            url_for('login')
        )

    return render_template(
        'index.html'
    )

# ==========================
# VIDEO ROUTE (NO SESSION CHECK NEEDED FOR LOGIN SCAN)
# ==========================

@app.route('/video')
def video():
    # Session check removed to allow the camera stream to display on the login page
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

# ==========================
# BIOMETRIC STATUS ROUTE (JSON API)
# ==========================

@app.route('/status')
def status():
    return {
        "blink": detector.blink_detected,
        "left_turn": detector.left_turn,
        "right_turn": detector.right_turn,
        "mouth_open": detector.mouth_open,
        "live_score": detector.live_score,
        "emotion": emotion,
        "voice_text": voice_text,
        "voice_status": voice_status
    }

# ==========================
# BIOMETRIC RESET ROUTE
# ==========================

@app.route('/reset_biometrics', methods=['POST'])
def reset_biometrics():
    detector.reset()
    global emotion, voice_text, voice_status
    emotion = "Neutral"
    voice_text = "..."
    voice_status = "Listening"
    return {"status": "success"}

# ==========================
# LOGOUT
# ==========================

@app.route('/logout')
def logout():

    session.pop(
        'user',
        None
    )
    detector.reset()

    return redirect(
        url_for('login')
    )

# ==========================
# MAIN
# ==========================

import webbrowser

if __name__ == "__main__":
    webbrowser.open("http://127.0.0.1:5000/login")
    app.run(debug=False, threaded=True, use_reloader=False)