python -m venv venv
./venv/scripts/activate
pip install requests
pip install flask
pip install pyaudio
pip install sounddevice
pip install webrtcvad
pip install python-dotenv

# If using openai whisper service

pip install openai

# If running whisper locally

pip install faster-whisper
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
