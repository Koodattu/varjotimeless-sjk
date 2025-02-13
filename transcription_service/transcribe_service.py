#!/usr/bin/env python
import os
import io
import time
import wave
import threading
import tempfile
import requests
import pyaudio
import webrtcvad
from flask import Flask, request, jsonify, Blueprint
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load configuration from .env
load_dotenv()
SERVICE_PORT = os.getenv("SERVICE_PORT", "8080")

TRANSCRIPTION_METHOD = os.getenv("TRANSCRIPTION_METHOD", "local")  # "local" or "rest"
TASK = os.getenv("TASK", "transcribe")  # "transcribe" or "translate"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Two REST endpoint URLs to send transcriptions (comma-separated in .env)
MEETING_SERVICE_URL = os.getenv("MEETING_SERVICE_URL", "")
MANAGER_SERVICE_URL = os.getenv("MANAGER_SERVICE_URL", "")

# For local transcription using faster-whisper
if TRANSCRIPTION_METHOD == "local":
    from faster_whisper import WhisperModel
    LOCAL_MODEL_SIZE = os.getenv("LOCAL_MODEL_SIZE", "large-v3-turbo")
    # Initialize the local model (using GPU if available)
    device = "cuda" if os.getenv("USE_CUDA", "False") == "True" else "cpu"
    local_model = WhisperModel(LOCAL_MODEL_SIZE, device=device, compute_type="float16")
else:
    local_model = None

# Audio configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
FRAME_DURATION = 30  # in ms (acceptable: 10, 20, or 30 ms)
FRAME_SIZE = int(RATE * FRAME_DURATION / 1000)  # number of samples per frame
SILENCE_DURATION = 1.5  # seconds of silence to mark end of speech segment

vad = webrtcvad.Vad(2)  # set aggressiveness from 0 (least) to 3 (most)

# Setup PyAudio to capture audio from the desired device (device index specified via .env)
AUDIO_DEVICE_INDEX = int(os.getenv("AUDIO_DEVICE_INDEX", "0"))
audio_interface = pyaudio.PyAudio()
stream = audio_interface.open(format=FORMAT,
                              channels=CHANNELS,
                              rate=RATE,
                              input=True,
                              frames_per_buffer=FRAME_SIZE,
                              input_device_index=AUDIO_DEVICE_INDEX)

def is_speech(frame: bytes) -> bool:
    return vad.is_speech(frame, RATE)

def save_frames_to_wav(frames, file_path):
    with wave.open(file_path, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio_interface.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))

def get_wav_bytes(frames) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio_interface.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))
    buf.seek(0)
    return buf.read()

def send_transcription(text: str, meeting_id: int = 0):
    def send_request(endpoint):
        try:
            requests.post(endpoint, json={"transcription": text})
        except Exception as e:
            if "Failed to establish a new connection" not in str(e):
                print(f"Error sending transcription to {endpoint}: {e}")

    REST_ENDPOINT_URLS = [
        urlparse(MEETING_SERVICE_URL, "/api/v1/meeting/", meeting_id, "/transcription"), 
        urlparse(MANAGER_SERVICE_URL, "/transcription")
    ]
    for endpoint in REST_ENDPOINT_URLS:
        if endpoint.strip():
            threading.Thread(target=send_request, args=(endpoint.strip(),), daemon=True).start()

def process_audio_segment(frames, meeting_id):
    print("Processing audio segment...")
    transcription = ""
    if TRANSCRIPTION_METHOD == "local":
        # Write to a temporary WAV file for faster-whisper
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            temp_filename = tmp_file.name
        try:
            save_frames_to_wav(frames, temp_filename)
            # Use the TASK parameter ("transcribe" or "translate")
            segments, _ = local_model.transcribe(temp_filename, task=TASK, beam_size=5, temperature=0.0)
            transcription = " ".join(seg.text for seg in segments).strip()
        except Exception as e:
            print(f"Local transcription error: {e}")
        finally:
            os.remove(temp_filename)
    else:
        try:
            wav_bytes = get_wav_bytes(frames)
            audio_buffer = io.BytesIO(wav_bytes)
            # Set the .name attribute so the API infers the file type
            audio_buffer.name = "audio.wav"
            from openai import OpenAI
            openai_client = OpenAI(api_key=OPENAI_API_KEY)
            # Using OpenAI's REST API for Whisper with correct usage
            if TASK == "transcribe":
                response = openai_client.audio.transcriptions.create(model="whisper-1", file=audio_buffer)
            elif TASK == "translate":
                response = openai_client.audio.translations.create(model="whisper-1", file=audio_buffer)
            else:
                response = {}
            transcription = response.text.strip()
        except Exception as e:
            print(f"REST transcription error: {e}")

    if transcription:
        print("Transcription:", transcription)
        send_transcription(transcription, meeting_id)
    else:
        print("No transcription produced.")

def create_new_meeting():
    try:
        response = requests.post(MEETING_SERVICE_URL + "/api/v1/meeting")
        meeting_id = response.json().get("id", 0)
        return str(meeting_id)
    except Exception as e:
        print("Error creating new meeting:", e)
        return "0"

def listen_loop():
    frames = []
    last_speech_time = None

    try:
        meeting_id = create_new_meeting()
        print("New meeting ID:", meeting_id)
        print("Listening on device index", AUDIO_DEVICE_INDEX)
        while True:
            frame = stream.read(FRAME_SIZE, exception_on_overflow=False)
            if is_speech(frame):
                if last_speech_time is None:
                    print("Speech detected...")
                last_speech_time = time.time()
                frames.append(frame)
            else:
                # If sufficient silence is detected after speech, process the segment
                if last_speech_time and (time.time() - last_speech_time) > SILENCE_DURATION and frames:
                    segment_frames = frames.copy()
                    threading.Thread(target=process_audio_segment, args=(segment_frames,meeting_id), daemon=True).start()
                    frames = []
                    last_speech_time = None
    except KeyboardInterrupt:
        print("Stopping listening...")
    finally:
        stream.stop_stream()
        stream.close()
        audio_interface.terminate()

# Create the Flask app
api_v0 = Blueprint('api_v0', __name__)
app = Flask(__name__)
app.register_blueprint(api_v0)

# REST endpoint to receive text from other services
@api_v0.route('/receive-text', methods=['POST'])
def receive_text():
    data = request.get_json(force=True)
    text = data.get("text", "")
    print("Received text via REST API:", text)
    return jsonify({"status": "success", "message": "Text received"}), 200

if __name__ == "__main__":
    # Start the listen loop in a separate daemon thread
    listener_thread = threading.Thread(target=listen_loop, daemon=True)
    listener_thread.start()

    # Start the Flask app
    app.run(host="0.0.0.0", port=SERVICE_PORT)