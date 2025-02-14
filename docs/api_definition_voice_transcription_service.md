# Voice Transcription Service API

## Overview
The Voice Transcription Service is a real-time speech-to-text system that listens for audio input, processes speech segments, and transcribes them using either a local or REST-based model. The service can also send transcriptions to external endpoints for further processing.

## Base URL
```
http://<host>:<port>/api/v0
```

## Environment Variables

| Variable                 | Description | Default Value |
|--------------------------|-------------|---------------|
| `SERVICE_PORT`           | Port on which the service runs | `8080` |
| `TRANSCRIPTION_METHOD`   | Method for transcription (`local` or `rest`) | `local` |
| `TASK`                   | Task for transcription (`transcribe` or `translate`) | `transcribe` |
| `OPENAI_API_KEY`         | API key for OpenAI Whisper (if using `rest` method) | N/A |
| `MEETING_SERVICE_URL`    | URL of the meeting service | N/A |
| `MANAGER_SERVICE_URL`    | URL of the manager service | N/A |
| `LOCAL_MODEL_SIZE`       | Size of the local `faster-whisper` model | `large-v3-turbo` |
| `USE_CUDA`               | Use GPU acceleration (`True` or `False`) | `False` |
| `AUDIO_DEVICE_INDEX`     | Index of the audio input device | `0` |

## Endpoints

### 1. Receive Text
Receive externally processed text via REST API.

**URL:**
```
POST /api/v0/receive-text
```

**Request Body:**
```json
{
  "text": "Transcribed text here"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Text received"
}
```

### 2. Create New Meeting
Create a new meeting session to associate with transcriptions.

**URL:**
```
POST <MEETING_SERVICE_URL>/meeting
```

**Response:**
```json
{
  "meeting_id": 1234
}
```

### 3. Send Transcription
Send transcribed text to external services.

**URL:**
```
POST <MEETING_SERVICE_URL>/meeting/{meeting_id}/transcription
POST <MANAGER_SERVICE_URL>/meeting/{meeting_id}/transcription
```

**Request Body:**
```json
{
  "transcription": "This is a sample transcription."
}
```

## Real-Time Speech Processing Workflow
1. The service continuously listens for audio input from the configured device.
2. Voice activity detection (VAD) segments speech from silence.
3. Detected speech is transcribed using either:
   - A local `faster-whisper` model (if `TRANSCRIPTION_METHOD=local`)
   - OpenAI's Whisper API (if `TRANSCRIPTION_METHOD=rest`)
4. Transcribed text is sent to the configured endpoints (`MEETING_SERVICE_URL`, `MANAGER_SERVICE_URL`).

## Error Handling
- If the meeting service is unavailable, the service retries creating a new meeting every 5 seconds.
- If a transcription request fails, an error is logged, but the service continues running.
- If an endpoint is unreachable, the system skips it without blocking execution.

## CORS Configuration
All API responses include the following CORS headers:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

