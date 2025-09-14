import os
import io
import time
import wave
import threading
import tempfile
import requests
import pyaudio
import webrtcvad
import uvicorn
from fastapi import FastAPI, Request, HTTPException, APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load configuration from .env
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    listener_thread = threading.Thread(target=listen_loop, daemon=True)
    listener_thread.start()
    yield
    # Shutdown
    listener_thread.join()

# Create the FastAPI app
app = FastAPI(lifespan=lifespan)
router = APIRouter(prefix="/api/v0")

SERVICE_PORT = os.getenv("TRANSCRIPTION_SERVICE_PORT")
TRANSCRIPTION_METHOD = os.getenv("TRANSCRIPTION_METHOD")
TASK = os.getenv("TASK")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MEETING_SERVICE_URL = os.getenv("MEETING_SERVICE_URL")
MANAGER_SERVICE_URL = os.getenv("MANAGER_SERVICE_URL")

# For local transcription using faster-whisper
if TRANSCRIPTION_METHOD == "local":
    from faster_whisper import WhisperModel
    LOCAL_MODEL_SIZE = os.getenv("LOCAL_MODEL_SIZE", "large-v3-turbo")
    # Initialize the local model (using GPU if available)
    device = "cuda" if os.getenv("USE_CUDA", "False") == "True" else "cpu"
    print(f"Initializing local model on {device}...")
    local_model = WhisperModel(LOCAL_MODEL_SIZE, device=device, compute_type="float16")
else:
    local_model = None

# Audio configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
FRAME_DURATION = 30  # in ms (acceptable: 10, 20, or 30 ms)
FRAME_SIZE = int(RATE * FRAME_DURATION / 1000)  # number of samples per frame
SILENCE_DURATION = 0.6  # seconds of silence to mark end of speech segment

vad = webrtcvad.Vad(1)  # set aggressiveness from 0 (least) to 3 (most)

# Setup PyAudio to capture audio from the desired device (device index specified via .env)
audio_interface = pyaudio.PyAudio()
AUDIO_DEVICE_INDEX = os.getenv("AUDIO_DEVICE_INDEX", "default")
if AUDIO_DEVICE_INDEX != "default":
    AUDIO_DEVICE_INDEX = int(AUDIO_DEVICE_INDEX)
else:
    AUDIO_DEVICE_INDEX = audio_interface.get_default_input_device_info()["index"]
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
        MEETING_SERVICE_URL + f"/meeting/{meeting_id}/transcription",
        MANAGER_SERVICE_URL + f"/meeting/{meeting_id}/transcription"
    ]
    for endpoint in REST_ENDPOINT_URLS:
        if endpoint:
            threading.Thread(target=send_request, args=(endpoint,), daemon=True).start()

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
        response = requests.post(MEETING_SERVICE_URL + "/meeting")
        return response.json().get("meeting_id", None)
    except Exception as e:
        print("Error creating new meeting:", e)
        return None

def listen_loop():
    frames = []
    last_speech_time = None

    try:
        meeting_id = None
        while not meeting_id:
            meeting_id = create_new_meeting()
            if not meeting_id:
                print("Retrying to create a new meeting...")
                time.sleep(5)

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
                if last_speech_time and (time.time() - last_speech_time) > SILENCE_DURATION and frames:
                    # Calculate segment duration in seconds
                    segment_duration = (len(frames) * FRAME_DURATION) / 1000.0
                    if segment_duration < 0.5:
                        print(f"Audio segment too short ({segment_duration:.2f} s), discarding...")
                    else:
                        segment_frames = frames.copy()
                        threading.Thread(target=process_audio_segment, args=(segment_frames, meeting_id), daemon=True).start()
                    frames = []
                    last_speech_time = None
    except KeyboardInterrupt:
        print("Stopping listening...")
    finally:
        stream.stop_stream()
        stream.close()
        audio_interface.terminate()

# REST endpoint to receive text from other services
@router.post("/receive-text")
async def receive_text(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from e
    text = data.get("text", "")
    print("Received text via REST API:", text)
    return JSONResponse(content={"status": "success", "message": "Text received"})

app.include_router(router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    print(f"Starting Transcription Service on port {SERVICE_PORT}")
    uvicorn.run("transcribe_service:app", host="0.0.0.0", port=int(SERVICE_PORT), workers=1, reload=False)