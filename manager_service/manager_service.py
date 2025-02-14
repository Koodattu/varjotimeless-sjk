import os
import time
import json
import requests
from openai import OpenAI
from flask import Flask, request, jsonify, Blueprint, Response, stream_with_context
from flask_cors import CORS
from pydantic import BaseModel
from urllib.parse import urljoin
from enum import Enum
from dotenv import load_dotenv
import queue

load_dotenv()

app = Flask(__name__)
api = Blueprint("api", __name__)

class MessageAnnouncer:
    def __init__(self):
        self.listeners = []

    def listen(self):
        q = queue.Queue(maxsize=5)
        self.listeners.append(q)
        return q

    def announce(self, msg):
        # Iterate over a copy so we can remove stale queues.
        for q in list(self.listeners):
            try:
                q.put_nowait(msg)
            except queue.Full:
                self.listeners.remove(q)

    def format_sse(self, data, event=None):
        msg = f"data: {json.dumps(data)}\n\n"
        if event is not None:
            msg = f"event: {event}\n" + msg
        return msg

    def publish(self, data, type='message'):
        event = self.format_sse(data, event=type)
        self.announce(event)

# Global in-memory SSE announcer instance
announcer = MessageAnnouncer()

@api.route('/sse')
def stream():
    def event_stream():
        q = announcer.listen()
        while True:
            msg = q.get()  # blocks until a new message arrives
            yield msg
    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")

# -----------------------------
# Application code below remains the same
# -----------------------------

class DiscussionState(Enum):
    CONCEPTUALIZATION = "Conceptualization"
    REQUIREMENT_ANALYSIS = "Requirement Analysis"
    DESIGN = "Design (Tech & UI/UX)"
    IMPLEMENTATION = "Implementation"
    TESTING = "Testing"
    DEPLOYMENT_MAINTENANCE = "Deployment and Maintenance"

# Global in-memory state
current_state = DiscussionState.CONCEPTUALIZATION.value
transcriptions = []             # List of received transcription messages
requirements = ""               # List of software requirements
notebook_summary = ""           # Summary of the discussion (the “notebook”)
code_generation_running = False  # Flag to indicate if a code generation job is running
deployment_url = ""             # URL where the generated code will be deployed

# Environment configuration for LLM providers and service URLs
SERVICE_PORT = os.environ.get("SERVICE_PORT", 8082)
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")  # "openrouter", "openai" or "ollama"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OLLAMA_URL = os.environ.get("OLLAMA_URL")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL")
VOICE_SERVICE_URL = os.environ.get("VOICE_SERVICE_URL")
MEETING_SERVICE_URL = os.environ.get("MEETING_SERVICE_URL")  # Assuming this provides the list of requirements
CODE_GENERATION_SERVICE_URL = os.environ.get("CODE_GENERATION_SERVICE_URL")

# Choose the model based on the provider, OpenAI, OpenRouter, or OLLAMA
CHOSEN_MODEL = OPENAI_MODEL if LLM_PROVIDER.lower() == "openai" else OPENROUTER_MODEL if LLM_PROVIDER.lower() == "openrouter" else OLLAMA_MODEL

# Setup LLM client based on provider choice.
def get_llm_client():
    if LLM_PROVIDER.lower() == "openrouter":
        return OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )
    elif LLM_PROVIDER.lower() == "openai":
        return OpenAI(
            api_key=OPENAI_API_KEY,
        )
    elif LLM_PROVIDER.lower() == "ollama":
        return OpenAI(
            base_url=OLLAMA_URL,
            api_key="ollama",  # Required but unused
        )
    else:
        raise ValueError("Unsupported LLM Provider")

llm_client = get_llm_client()

# -------------------------------------------------------------------
# LLM Helper Functions
# -------------------------------------------------------------------

class ImmediateAction(BaseModel):
    take_action: bool

def poll_immediate_action(transcription):
    """
    Poll the LLM to decide if immediate action is needed based on the latest transcription.
    The prompt asks for a True/False answer.
    """
    system_prompt = (
        "You are a meeting assistant for a software development meeting focused on creating new software. "
        "Analyze the provided transcription snippet and determine if the content indicates that an immediate action is required. "
        "Return your answer as a valid JSON with a single field 'take_action' set to true or false. Do not include any extra commentary."
    )
    user_prompt = f"Transcription snippet: '{transcription}'"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    try:
        response = llm_client.beta.chat.completions.parse(
            model=CHOSEN_MODEL,
            messages=messages,
            max_tokens=10,
            response_format=ImmediateAction
        )
        result = response.choices[0].message.parsed.take_action
        print(f"Immediate action LLM response: {result}")
        return result
    except Exception as e:
        print("Error in poll_immediate_action:", e)
        return False

def update_notebook_summary(current_notebook, transcriptions):
    """
    Poll the LLM to update the notebook summary with the latest transcription.
    The prompt includes the current summary and the new transcription.
    """
    system_prompt = (
        "You are a summarization assistant for a software development meeting about creating new software. "
        "Your task is to update the current notebook summary to concisely capture all discussion points, decisions, and evolving requirements. "
        "Focus on clarity and brevity in your summary."
    )
    user_prompt = (
        f"Current notebook summary: '{current_notebook}'\n"
        "New transcriptions:\n" + "\n".join(transcriptions)
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    try:
        response = llm_client.chat.completions.create(
            model=CHOSEN_MODEL,
            messages=messages,
            max_tokens=100,
        )
        new_summary = response.choices[0].message.content.strip()
        print(f"Updated notebook summary: {new_summary}")
        return new_summary
    except Exception as e:
        print("Error in update_notebook_summary:", e)
        return current_notebook

def get_requirements(meeting_id):
    """
    Retrieve the list of requirements from the Meeting Service (or other service).
    Expects a JSON response with a "requirements" field.
    """
    try:
        full_url = urljoin(MEETING_SERVICE_URL, f"meeting/{meeting_id}/requirements")
        response = requests.get(full_url)
        if response.status_code == 200:
            data = response.json()
            reqs = data.get("requirements", "")
            print(f"Fetched requirements: {reqs}")
            return reqs
        else:
            print("Failed to fetch requirements, status:", response.status_code)
            return ""
    except Exception as e:
        print("Error fetching requirements:", e)
        return ""

class EvaluatedState(BaseModel):
    updated_state: DiscussionState
    generate_code: bool
    feedback: str

def evaluate_and_maybe_update_state(current_state, requirements, notebook, transcription):
    """
    Poll the LLM with the current state, requirements, notebook summary, and latest transcription.
    """
    system_prompt = (
        '''
        You are a strategic meeting assistant for a software development meeting.
        The current discussion state can only be one of the following: Conceptualization -> Requirement Analysis -> Design (Tech & UI/UX) -> Implementation -> Testing -> Deployment and Maintenance.
        The discussion should be moving through these states in the aforementioned order.
        Based on the provided context, determine whether to update the state (choose one of these values) and whether to trigger code generation.
        If the users demand for code generation, you should trigger the code generation service.
        Respond with a valid JSON object containing an 'updated_state' key (with one of the allowed enum values (it can be the same if no change is needed)) and a boolean 'generate_code' flag, along with brief feedback.
        '''
    )
    user_prompt = (
        f"Current state: '{current_state}'\n"
        f"Requirements: '{requirements}'\n"
        f"Notebook summary: '{notebook}'\n"
        f"Latest transcription: '{transcription}'"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    try:
        response = llm_client.beta.chat.completions.parse(
            model=CHOSEN_MODEL,
            messages=messages,
            max_tokens=150,
            response_format=EvaluatedState
        )
        result = response.choices[0].message.parsed
        print(f"State evaluation LLM response: {result}")
        updated_state = result.updated_state
        generate_code = result.generate_code
        feedback = result.feedback
        return updated_state, generate_code, feedback
    except Exception as e:
        print("Error in evaluate_and_maybe_update_state:", e)
        return current_state, False, ""

def trigger_code_generation(requirements):
    """
    Call the external code generation service. This call is expected to have a very long timeout.
    """
    payload = {
        "requirements": requirements,
    }
    try:
        full_url = urljoin(CODE_GENERATION_SERVICE_URL, "generate")
        response = requests.post(full_url, json=payload, timeout=36000)
        if response.status_code == 200:
            print("Code generation triggered successfully.")
            return response.json()
        else:
            print("Code generation service error, status:", response.status_code)
            return {}
    except Exception as e:
        print("Error triggering code generation:", e)
        return {}

# -------------------------------------------------------------------
# Flask Endpoints
# -------------------------------------------------------------------

@api.route("/meeting/<meeting_id>/transcription", methods=["POST"])
def receive_transcription(meeting_id):
    """
    Endpoint to receive a new transcription.
    1. Stores the transcription.
    2. Polls the LLM for an immediate action decision.
    3. If more than 5 transcriptions exist, updates the notebook summary.
    4. If immediate action is requested, evaluates whether to update state and/or trigger code generation.
    """
    global transcriptions, notebook_summary, current_state, code_generation_running, requirements, deployment_url

    data = request.get_json()
    transcription = data.get("transcription", "").strip()
    if not transcription:
        return jsonify({"status": "Error", "message": "No transcription provided."}), 400

    # Add transcription to our in-memory list
    transcriptions.append(transcription)
    print(f"Received transcription: {transcription}")
    # Publish transcription via SSE (using our custom announcer)
    announcer.publish({"transcription": transcription}, type='transcription')

    # Decide if we need to act immediately
    immediate_action = poll_immediate_action(transcription)

    # Update notebook summary if we have more than 5 transcriptions
    if len(transcriptions) % 5 == 0:
        notebook_summary = update_notebook_summary(notebook_summary, transcriptions)
        transcriptions = transcriptions[-5:]  # Keep only the last 5 transcriptions
        announcer.publish({"notebook_summary": notebook_summary}, type='notebook_summary')

    # If no immediate action, simply store the transcription and return
    if not immediate_action:
        return jsonify({"status": "OK", "message": "Transcription stored, no further action."}), 200

    # Immediate action is needed: retrieve requirements from the meeting service
    requirements = get_requirements(meeting_id)
    announcer.publish({"requirements": requirements}, type='requirements')

    # Evaluate current state and whether to trigger code generation
    new_state, generate_code, feedback = evaluate_and_maybe_update_state(current_state, requirements, notebook_summary, transcription)

    print(f"LLM feedback: {feedback}")

    if new_state != current_state:
        current_state = new_state
        print(f"Updated discussion state to: {current_state}")
        announcer.publish({"current_state": new_state}, type='current_state')

    if generate_code:
        if not code_generation_running:
            code_generation_running = True
            announcer.publish({"code_generation_running": code_generation_running}, type='code_generation_running')
            result = trigger_code_generation(requirements)
            deployment_url = result.get("deployment_url", "")
            announcer.publish({"deployment_url": deployment_url}, type='deployment_url')
            code_generation_running = False
            announcer.publish({"code_generation_running": code_generation_running}, type='code_generation_running')
            return jsonify({"status": "OK", "message": "Code generation triggered.", "result": result}), 200
        else:
            return jsonify({"status": "OK", "message": "Code generation already running."}), 200

    return jsonify({"status": "OK", "message": "Transcription processed."}), 200

@api.route("/everything", methods=["GET"])
def get_everything():
    data = { 
        "transcriptions": transcriptions, 
        "notebook_summary": notebook_summary, 
        "current_state": current_state,
        "code_generation_running": code_generation_running,
        "requirements": requirements,
        "deployment_url": deployment_url,
    }
    return jsonify(data), 200

if __name__ == "__main__":
    app.register_blueprint(api, url_prefix="/api/v0")
    CORS(app)
    app.run(host="0.0.0.0", port=SERVICE_PORT, debug=True)
