from flask import Flask, Response, render_template, request, redirect, url_for, session
import cv2
import numpy as np
from detect import LivenessDetector
import os

app = Flask(__name__)
app.secret_key = "secret123"

USERNAME = "admin"
PASSWORD = "1234"

detector = LivenessDetector()

def generate_frames():
    while True:
        # Create dummy frame (no camera on server)
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 255

        cv2.putText(frame, "Camera not supported on server",
                    (50, 240),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (0, 0, 255), 2)

        frame = detector.process(frame)
        frame = detector.draw_ui(frame)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ""
    if request.method == 'POST':
        if request.form['username'] == USERNAME and request.form['password'] == PASSWORD:
            session['user'] = USERNAME
            return redirect(url_for('index'))
        else:
            error = "Invalid Credentials"
    return render_template('login.html', error=error)


@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')


@app.route('/video')
def video():
    if 'user' not in session:
        return redirect(url_for('login'))

    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
