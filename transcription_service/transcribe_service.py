import time
import threading
import requests
import logging
from RealtimeSTT import AudioToTextRecorder

# Configuration
#WHISPER_MODEL = "deepdml/faster-whisper-large-v3-turbo-ct2"  # Replace with your actual Whisper model
WHISPER_MODEL = "large-v3-turbo"  # Replace with your actual Whisper model
AUDIO_DEVICE_INPUT_ID = 1#7#1#3  # Set to your audio input device index if needed
REST_ENDPOINT_URL = "http://localhost:5000/transcription"  # Replace with your actual REST endpoint

def send_transcription(text):
    """
    Sends the transcribed text to the REST endpoint asynchronously.
    """
    def send_request():
        try:
            response = requests.post(REST_ENDPOINT_URL, json={"transcription": text})
            # Optionally, handle the response if needed
        except Exception as e:
            error = e
            print(f"Error sending transcription: {e}")

    # Start a new daemon thread for each request to avoid blocking
    thread = threading.Thread(target=send_request, daemon=True)
    thread.start()

def process_text(text):
    """
    Callback function that processes the transcribed text.
    It sends the text to the REST endpoint if it's not empty.
    """
    text = text.strip()
    if text:
        print(text, end=" ")
        send_transcription(text)

def main():
    # Initialize the AudioToTextRecorder with minimal configuration
    recorder_config = {
        'spinner': False,
        'model': WHISPER_MODEL,  # Specify the Whisper model you want to use
        'use_microphone': True,
        'input_device_index': AUDIO_DEVICE_INPUT_ID,  # Set to your audio input device index if needed
        'silero_sensitivity': 0.6,
        'silero_use_onnx': True,
        'post_speech_silence_duration': 0.6,  # adjust as needed
        'min_length_of_recording': 0.2,
        'min_gap_between_recordings': 0.2,
        'enable_realtime_transcription': False,
        'compute_type': 'auto',
        'language': 'en',
        'initial_prompt': ("People: Juha Ala-Rantala, Jussi Rasku, Joni Honkanen"),
        'level': logging.ERROR,  # Disable internal logging or set as needed
    }

    try:
        recorder = AudioToTextRecorder(**recorder_config)
        print("RealtimeSTT Sender is running. Press Ctrl+C to exit.")
        print("Transcription:", end=" ")

        while True:
            if recorder:
                recorder.text(process_text)
            time.sleep(0.1)  # Short sleep to prevent CPU overuse

    except KeyboardInterrupt:
        print("\nShutting down RealtimeSTT Sender.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if recorder:
            recorder.stop()  # Ensure the recorder is properly stopped

if __name__ == "__main__":
    main()
