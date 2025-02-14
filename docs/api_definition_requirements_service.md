# Requirements Management REST API

This REST API provides an interface for managing evolving software project requirements through transcriptions of meeting discussions. The API supports creating meetings, submitting transcriptions, and retrieving updated requirements.

## Base URL

```
http://<host>:<port>/api/v0
```

## Authentication

No authentication is required for this API.

---

## Endpoints

### 1. Create a New Meeting

**Endpoint:**
```
POST /meeting
```

**Description:**
Creates a new meeting and returns a unique meeting ID.

**Request Body:**
_None_

**Response:**
```json
{
  "meeting_id": "<uuid>"
}
```

**Response Codes:**
- `201 Created` – Meeting created successfully.

---

### 2. Submit a Transcription

**Endpoint:**
```
POST /meeting/<meeting_id>/transcription
```

**Description:**
Adds a transcription entry to a specific meeting. If enough transcriptions are submitted (threshold defined by `REQUIREMENT_UPDATE_INTERVAL`), the system updates the project requirements.

**Request Body:**
```json
{
  "transcription": "Meeting discussion text here."
}
```

**Response:**
```json
{
  "status": "OK",
  "message": "Transcription received."
}
```

or

```json
{
  "status": "OK",
  "message": "Requirements updated."
}
```

**Response Codes:**
- `200 OK` – Transcription received.
- `400 Bad Request` – No transcription provided.
- `404 Not Found` – Meeting ID not found.

---

### 3. Retrieve Current Requirements

**Endpoint:**
```
GET /meeting/<meeting_id>/requirements
```

**Description:**
Fetches the latest requirements list for a specific meeting. If new transcriptions exist, the system updates the requirements before returning them.

**Response:**
```json
{
  "status": "OK",
  "requirements": "- Requirement 1\n- Requirement 2\n- Requirement 3"
}
```

**Response Codes:**
- `200 OK` – Requirements retrieved successfully.
- `404 Not Found` – Meeting ID not found.

---

## CORS Support

This API allows cross-origin requests with the following headers:
- `Access-Control-Allow-Origin: *`
- `Access-Control-Allow-Methods: GET, POST, OPTIONS`
- `Access-Control-Allow-Headers: Content-Type`

---

## Error Handling

Errors are returned in the following format:
```json
{
  "status": "Error",
  "message": "Detailed error message here."
}
```

Common error cases include:
- `400 Bad Request` – Missing or invalid input.
- `404 Not Found` – Requested resource does not exist.
- `500 Internal Server Error` – Unexpected server failure.

---

## Environment Variables

The service configuration is managed through environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICE_PORT` | Port for the Flask application | `8081` |
| `LLM_PROVIDER` | LLM provider (`openai`, `openrouter`, `ollama`) | `openai` |
| `OPENROUTER_API_KEY` | API key for OpenRouter | `None` |
| `OPENROUTER_MODEL` | Model name for OpenRouter | `None` |
| `OPENAI_API_KEY` | API key for OpenAI | `None` |
| `OPENAI_MODEL` | Model name for OpenAI | `gpt-4o-mini` |
| `OLLAMA_URL` | Base URL for Ollama | `None` |
| `OLLAMA_MODEL` | Model name for Ollama | `None` |
| `REQUIREMENT_UPDATE_INTERVAL` | Number of transcriptions required to update requirements | `5` |

---

## Running the Service

Ensure all required environment variables are set before running the application:

```sh
export SERVICE_PORT=8081
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your-api-key
export OPENAI_MODEL=gpt-4o-mini
python app.py
```

The service will be available at `http://0.0.0.0:8081/api/v0`.

---

## License

This project is licensed under the MIT License.

