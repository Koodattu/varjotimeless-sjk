import json
import os
import requests
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit

###########################
# GLOBAL CONFIG / STATE
###########################

# Where to call your LLM
LLM_API_URL = "http://localhost:11434/api/generate"
LLM_MODEL = "qwen2.5:7b-instruct-q4_K_M"

# Example endpoints for the other services:
CONTEXT_SERVICE_URL = "http://localhost:5001/requirements"       # GET
CODE_GENERATION_URL = "http://localhost:5002/codegen"            # POST

# Global state (in-memory for simplicity)
STATE = {
    "code_generation_in_progress": False,
    "latest_transcription": "",
    "latest_requirements": "",
    "deployed_url": ""
}

###########################
# FLASK APP + SOCKET.IO
###########################

app = Flask(__name__, template_folder='.')
socketio = SocketIO(app, cors_allowed_origins="*")

###########################
# LLM HELPERS
###########################

def call_llm(prompt: str, schema: dict = None, timeout=30) -> dict:
    """
    Calls your LLM API with the given prompt.
    If a schema is provided, it requests structured JSON output.
    Returns a parsed JSON object or fallback to an empty dict on errors.
    """
    payload = {
        "prompt": prompt,
        "model": LLM_MODEL,
        "stream": False
    }

    if schema:
        payload["format"] = schema

    try:
        resp = requests.post(LLM_API_URL, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        response_text = data.get("response", "{}").strip()
        return json.loads(response_text)  # Parse the structured JSON
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(f"[LLM Error] {e}")
        return {}  # Return empty dict as fallback


def decide_if_fetch_requirements(transcription: str) -> bool:
    """
    Decides if requirements should be fetched based on the latest transcription.
    Uses a structured JSON prompt.
    """
    prompt = f"""
You are a decision-making assistant for a software project.
Based on the transcription provided below, decide if the context service's requirements should be fetched.
Respond with structured JSON using the following schema:

Schema:
{{
  "check_requirements": true/false
}}

Transcription:
{transcription}
"""
    schema = {
        "type": "object",
        "properties": {
            "check_requirements": {"type": "boolean"}
        },
        "required": ["check_requirements"]
    }

    response = call_llm(prompt, schema)
    return response.get("check_requirements", False)


def decide_if_proceed_with_code_generation(transcription: str, requirements: str) -> bool:
    """
    Decides if code generation should proceed based on transcription and requirements.
    Uses a structured JSON prompt.
    """
    prompt = f"""
You are a decision-making assistant for a software project.
Below is the transcription from the discussion and the requirements retrieved from the context service.
Determine if we should proceed with code generation.

Transcription:
{transcription}

Requirements:
{requirements}

Respond with structured JSON using the following schema:

Schema:
{{
  "proceed_with_code_generation": true/false
}}
"""
    schema = {
        "type": "object",
        "properties": {
            "proceed_with_code_generation": {"type": "boolean"}
        },
        "required": ["proceed_with_code_generation"]
    }

    response = call_llm(prompt, schema)
    return response.get("proceed_with_code_generation", False)


###########################
# FLASK ROUTES
###########################

@app.route("/")
def index():
    """Serve the barebones UI."""
    return render_template("index.html")


@app.route("/transcription", methods=["POST"])
def receive_transcription():
    """
    Endpoint that the live transcription service calls with JSON:
      {
        "text": "...the transcribed text..."
      }
    This will run the LLM decision logic, possibly fetch requirements,
    and possibly call the code generation service.
    """
	
    transcription_text = request.json.get("transcription", "")
    STATE["latest_transcription"] = transcription_text
    broadcast_state()
    if STATE["code_generation_in_progress"]:
        # If we are currently generating code, ignore new transcription or just store it
        # so we don't conflict. For simplicity, just store it.
        return jsonify({"status": "OK", "message": "Received, but code generation in progress"}), 200

    # 1) Store the new transcription

    # 2) Ask the LLM if we should fetch context
    should_fetch = decide_if_fetch_requirements(transcription_text)
    requirements_text = ""
    if should_fetch:
        # 3) If yes, fetch from the context service (GET)
        try:
            resp = requests.get(CONTEXT_SERVICE_URL, timeout=10)
            resp.raise_for_status()
            requirements_text = resp.text.strip()
        except Exception as e:
            requirements_text = f"(Error fetching requirements: {e})"
    STATE["latest_requirements"] = requirements_text

    # 4) If we have requirements, ask LLM if we want to proceed with code generation
    proceed = False
    if requirements_text:
        proceed = decide_if_proceed_with_code_generation(transcription_text, requirements_text)

    if proceed:
        # 5) Mark code generation in progress, POST to code generation service, wait for a result
        STATE["code_generation_in_progress"] = True
        broadcast_state()

        try:
            # Submit the requirements
            codegen_resp = requests.post(
                CODE_GENERATION_URL,
                json={"requirements": requirements_text},
                timeout=300
            )
            codegen_resp.raise_for_status()
            data = codegen_resp.json()
            # The codegen service returns e.g. { "deployed_url": "https://example.com/app123" }
            STATE["deployed_url"] = data.get("deployed_url", "")
        except Exception as e:
            STATE["deployed_url"] = f"Error during codegen: {e}"

        # 6) Done
        STATE["code_generation_in_progress"] = False

    # Finally, broadcast the updated state to all clients
    broadcast_state()
    return jsonify({"status": "OK"}), 200


###########################
# SOCKET.IO EVENTS
###########################

@socketio.on("request_state")
def handle_request_state():
    broadcast_state()


def broadcast_state():
    """Send the entire STATE dict to all connected Socket.IO clients."""
    socketio.emit("update_state", STATE)


###########################
# MAIN ENTRY
###########################

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
