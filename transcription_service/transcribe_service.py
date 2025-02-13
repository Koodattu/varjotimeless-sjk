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
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load configuration from .env
load_dotenv()
TRANSCRIPTION_METHOD = os.getenv("TRANSCRIPTION_METHOD", "local")  # "local" or "rest"
TASK = os.getenv("TASK", "transcribe")  # "transcribe" or "translate"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Two REST endpoint URLs to send transcriptions (comma-separated in .env)
REST_ENDPOINT_URLS = os.getenv("REST_ENDPOINT_URLS", "").split(",")

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

def send_transcription(text: str):
    def send_request(endpoint):
        try:
            requests.post(endpoint, json={"transcription": text})
        except Exception as e:
            print(f"Error sending transcription to {endpoint}: {e}")

    for endpoint in REST_ENDPOINT_URLS:
        if endpoint.strip():
            threading.Thread(target=send_request, args=(endpoint.strip(),), daemon=True).start()

def process_audio_segment(frames):
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
        # REST API: prepare an in-memory WAV buffer.
        try:
            wav_bytes = get_wav_bytes(frames)
            audio_buffer = io.BytesIO(wav_bytes)
            # Set the .name attribute so the API infers the file type
            audio_buffer.name = "audio.wav"
            from openai import OpenAI
            openai_client = OpenAI(OPENAI_API_KEY)
            # Using OpenAI's REST API for Whisper with correct usage
            if TASK == "transcribe":
                response = openai_client.audio.transcriptions.create("whisper-1", audio_buffer)
            elif TASK == "translate":
                response = openai_client.audio.translations.create("whisper-1", audio_buffer)
            else:
                response = {}
            transcription = response.get("text", "").strip() if isinstance(response, dict) else ""
        except Exception as e:
            print(f"REST transcription error: {e}")

    if transcription:
        print("Transcription:", transcription)
        send_transcription(transcription)
    else:
        print("No transcription produced.")

def listen_loop():
    frames = []
    last_speech_time = None

    print("Listening on device index", AUDIO_DEVICE_INDEX)
    try:
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
                    threading.Thread(target=process_audio_segment, args=(segment_frames,), daemon=True).start()
                    frames = []
                    last_speech_time = None
    except KeyboardInterrupt:
        print("Stopping listening...")
    finally:
        stream.stop_stream()
        stream.close()
        audio_interface.terminate()

# Create the Flask app
app = Flask(__name__)

# REST endpoint to receive text from other services
@app.route('/receive-text', methods=['POST'])
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
    app.run(host="0.0.0.0", port=5000)
