from flask import Flask, Response, render_template, request, redirect, url_for, session
import cv2
from detect import LivenessDetector
from deepface import DeepFace
import speech_recognition as sr
import threading

app = Flask(__name__)
app.secret_key = "secret123"   # 🔐 required for login

# 🔐 Login credentials (you can change)
USERNAME = "admin"
PASSWORD = "1234"

detector = LivenessDetector()

# 🎤 Voice setup
recognizer = sr.Recognizer()
mic = sr.Microphone()

voice_text = "Say something..."

def listen_voice():
    global voice_text
    try:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=2, phrase_time_limit=3)

        text = recognizer.recognize_google(audio)
        voice_text = text

    except:
        pass


def draw_text_with_bg(frame, text, x, y, text_color, bg_color):
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.8
    thickness = 2

    (w, h), _ = cv2.getTextSize(text, font, scale, thickness)

    # background
    cv2.rectangle(frame, (x, y - h - 10), (x + w, y + 5), bg_color, -1)

    # text
    cv2.putText(frame, text, (x, y),
                font, scale, text_color, thickness)


def generate_frames():
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not camera.isOpened():
        print("❌ Camera not opened")
        return

    print("✅ Camera started in Flask")

    frame_count = 0
    emotion = "Detecting..."
    voice_counter = 0

    while True:
        success, frame = camera.read()

        if not success or frame is None:
            continue

        frame = cv2.flip(frame, 1)

        # 🔹 Liveness Detection
        try:
            frame = detector.process(frame)
            frame = detector.draw_ui(frame)
        except Exception as e:
            print("Liveness error:", e)

        # 🔹 Emotion Detection (optimized)
        frame_count += 1
        if frame_count % 20 == 0:
            try:
                result = DeepFace.analyze(
                    frame,
                    actions=['emotion'],
                    enforce_detection=False
                )
                emotion = result[0]['dominant_emotion']
            except Exception as e:
                print("Emotion error:", e)

        # 🔹 Voice Detection (controlled)
        voice_counter += 1
        if voice_counter % 100 == 0:
            threading.Thread(target=listen_voice, daemon=True).start()

        voice_display = voice_text[:25]

        # 🎯 Draw text (clean UI)
        draw_text_with_bg(frame,
                          f'Emotion: {emotion}',
                          20, 40,
                          (255, 255, 255),
                          (0, 0, 0))

        draw_text_with_bg(frame,
                          f'Voice: {voice_display}',
                          20, 80,
                          (0, 0, 0),        # dark text
                          (255, 255, 255))  # light bg

        # Convert frame
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue

        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# 🔐 LOGIN ROUTE
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ""

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == USERNAME and password == PASSWORD:
            session['user'] = username
            return redirect(url_for('index'))
        else:
            error = "Invalid Credentials"

    return render_template('login.html', error=error)


# 🔐 PROTECTED HOME
@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')


# 🔐 PROTECTED VIDEO
@app.route('/video')
def video():
    if 'user' not in session:
        return redirect(url_for('login'))

    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


# 🔐 LOGOUT
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True)