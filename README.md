# AI Liveness Detection System

<p align="center">

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge)
![Flask](https://img.shields.io/badge/Flask-Web%20Application-black?style=for-the-badge)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-green?style=for-the-badge)
![TensorFlow](https://img.shields.io/badge/TensorFlow-Deep%20Learning-orange?style=for-the-badge)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Face%20Mesh-red?style=for-the-badge)
![DeepFace](https://img.shields.io/badge/DeepFace-Emotion%20Recognition-purple?style=for-the-badge)
![Vosk](https://img.shields.io/badge/Vosk-Voice%20Recognition-blueviolet?style=for-the-badge)

</p>

---

# Overview

AI Liveness Detection System is a Flask-based biometric authentication application that verifies whether the user is physically present in front of the camera.

The system combines multiple AI technologies including:

- Face Liveness Detection
- Facial Emotion Recognition
- Voice Recognition
- Secure Login Authentication
- Real-Time Camera Processing

Unlike traditional face verification systems, this project performs multiple liveness checks such as blinking, head movement, and mouth opening before granting access.

---

# Features

✅ Face Detection

Detects the user's face in real time using OpenCV and MediaPipe.

---

✅ Blink Detection

Detects natural eye blinking to verify that the face belongs to a real person.

---

✅ Head Movement Detection

Detects both left and right head movement.

---

✅ Mouth Open Detection

Verifies user interaction by detecting mouth opening.

---

✅ Liveness Score

Calculates a real-time liveness score based on successful biometric actions.

---

✅ Emotion Recognition

Recognizes emotions including:

- Happy
- Sad
- Angry
- Fear
- Surprise
- Neutral
- Disgust

using DeepFace.

---

✅ Voice Recognition

Uses the offline Vosk speech recognition engine to recognize spoken voice commands.

---

✅ Secure Login

The system allows login only after successful biometric verification.

---

✅ Real-Time Dashboard

Displays

- Live/Spoof Status
- Emotion
- Voice Status
- Voice Transcript
- Liveness Score

in real time.

---

# Tech Stack

| Technology | Purpose |
|------------|---------|
| Python | Programming Language |
| Flask | Backend Web Framework |
| OpenCV | Camera Processing |
| MediaPipe | Face Landmark Detection |
| TensorFlow | AI Model |
| DeepFace | Emotion Recognition |
| Vosk | Offline Voice Recognition |
| HTML | Frontend |
| CSS | Styling |
| JavaScript | Frontend Logic |

---

# Folder Structure

```
liveness-detection-system/

│
├── app.py
├── detect.py
├── requirements.txt
├── liveness_model.h5
├── liveness.keras
│
├── templates/
│     ├── index.html
│     └── login.html
│
├── static/
│     ├── css/
│     └── js/
│
├── resources/
│
├── src/
│
├── liveness/
│
├── vosk-model-small-en-us-0.15/
│
└── README.md
```

---

# Installation

Clone the repository

```bash
git clone https://github.com/punyakshii/liveness-detection-system.git
```

Move into the project directory

```bash
cd liveness-detection-system
```

Create Virtual Environment

```bash
python -m venv .venv
```

Activate Virtual Environment

Windows

```bash
.venv\Scripts\activate
```

Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

# Run the Project

```bash
python app.py
```

Open your browser

```
http://127.0.0.1:5000/login
```


# Working Process

1. User opens the login page.
2. Camera starts automatically.
3. Face is detected.
4. User performs liveness actions.
5. Emotion is detected.
6. Voice is recognized.
7. Liveness score is calculated.
8. If verification is successful, login is allowed.

---

# Future Improvements

- Face Anti-Spoofing using Deep Learning
- Face Recognition for Multiple Users
- Database Integration
- User Registration Module
- OTP Authentication
- Cloud Deployment
- Docker Support
- Mobile Application
- Performance Optimization
- User Activity Logging

---

# Requirements

- Python 3.10+
- Webcam
- Microphone
- Windows/Linux

---

# Author

**Punyakshi Solanki**

B.Tech Data Science Engineering

GitHub:
https://github.com/punyakshii

LinkedIn:
https://www.linkedin.com/in/punyakshi-solanki-89b24b298/

---

# License

This project is developed for educational and learning purposes.

---

# Acknowledgements

- OpenCV
- MediaPipe
- TensorFlow
- DeepFace
- Vosk
- Flask

---

⭐ If you found this project useful, consider giving it a Star on GitHub.
