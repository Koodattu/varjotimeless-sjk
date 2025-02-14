# Software Development Meeting Assistant API

This API facilitates real-time transcription processing, state management, and code generation for software development meetings.

## Base URL
```
http://<host>:<port>/api/v0
```

## Authentication
No authentication is required for this API.

## Endpoints

### 1. Receive Transcription
**Endpoint:**
```
POST /meeting/<meeting_id>/transcription
```
**Description:**
Processes and stores a new transcription, determines whether immediate action is required, updates the meeting notebook summary, evaluates state transitions, and triggers code generation if applicable.

**Request Parameters:**
- `meeting_id` (string, path) - The unique identifier of the meeting.
- Body (JSON):
  ```json
  {
    "transcription": "Discuss implementing a new authentication system."
  }
  ```

**Response:**
- **200 OK** if the transcription is processed successfully.
- **400 Bad Request** if no transcription is provided.

**Response Example:**
```json
{
  "status": "OK",
  "message": "Transcription processed."
}
```

---

### 2. Server-Sent Events (SSE) Stream
**Endpoint:**
```
GET /sse
```
**Description:**
Provides a live event stream of meeting state updates, transcriptions, and ongoing discussions.

**Response Format:**
- The response is a stream of JSON objects:
  ```json
  data: {
    "transcriptions": [...],
    "notebook_summary": "Latest meeting summary...",
    "current_state": "Design (Tech & UI/UX)",
    "code_generation_running": false,
    "requirements": "System must support multi-factor authentication.",
    "deployment_url": "http://deployment.example.com"
  }
  ```

**Notes:**
- The stream automatically updates every second.
- Can be used to monitor live meeting status.

---

## Discussion States
The discussion progresses through predefined states:
1. **Conceptualization**
2. **Requirement Analysis**
3. **Design (Tech & UI/UX)**
4. **Implementation**
5. **Testing**
6. **Deployment and Maintenance**

## Code Generation
When code generation is triggered, an external service is called with the software requirements. If successful, the generated code is deployed, and the `deployment_url` field in the SSE stream updates with the deployment location.

## Error Handling
The API returns standard HTTP status codes:
- **200 OK**: Request was processed successfully.
- **400 Bad Request**: Missing or invalid request parameters.
- **500 Internal Server Error**: An unexpected error occurred.

## Notes
- Ensure the `LLM_PROVIDER` environment variable is set correctly (`openai`, `openrouter`, or `ollama`).
- External dependencies include OpenAI API, OpenRouter, or Ollama, and a code generation service.
- Meeting discussions are summarized dynamically, with updates happening every 5 transcriptions.

