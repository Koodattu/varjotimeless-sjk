import os
import json
import requests
from openai import OpenAI
from flask import Flask, request, jsonify, Blueprint
from pydantic import BaseModel
from urllib.parse import urljoin

api_v0 = Blueprint('api_v0', __name__)
app = Flask(__name__)
app.register_blueprint(api_v0)

# Global in-memory state
transcriptions = []             # List of received transcription messages
notebook_summary = ""           # Summary of the discussion (the “notebook”)
current_state = "Conceptualization"  # Discussion state; possible states: 
                                    # Conceptualization > Requirement Analysis > Design (Tech & UI/UX) > Implementation > Testing > Deployment and Maintenance
code_generation_running = False  # Flag to indicate if a code generation job is running

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
FRONTEND_URL = os.environ.get("FRONTEND_URL")

CHOSEN_MODEL = ""

# Setup LLM client based on provider choice.
def get_llm_client():
    if LLM_PROVIDER.lower() == "openrouter":
        # Using OpenRouter via OpenAI SDK wrapper example.
        global CHOSEN_MODEL
        CHOSEN_MODEL = OPENROUTER_MODEL
        return OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )
    elif LLM_PROVIDER.lower() == "openai":
        global CHOSEN_MODEL
        CHOSEN_MODEL = OPENAI_MODEL
        return OpenAI(
            api_key=OPENAI_API_KEY,
        )
    elif LLM_PROVIDER.lower() == "ollama":
        global CHOSEN_MODEL
        CHOSEN_MODEL = OLLAMA_MODEL
        return OpenAI(
            base_url=OLLAMA_URL,
            api_key="ollama",  # Required but unused
            model=OLLAMA_MODEL,
        )
    else:
        raise ValueError("Unsupported LLM Provider")

llm_client = get_llm_client()

# -----------------------------------------------------------------------------
# LLM Helper Functions
# -----------------------------------------------------------------------------

class ImmediateAction(BaseModel):
    take_action: bool

def poll_immediate_action(transcription):
    """
    Poll the LLM to decide if immediate action is needed based on the latest transcription.
    The prompt asks for a True/False answer.
    """
    prompt = (
        f"Given the latest user transcription in the user message.\n"
        "Should we perform any immediate action? Respond with True or False only.\n"
        "Respond in valid JSON only."
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": transcription}
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
    prompt = (
        f"Current notebook summary: '{current_notebook}'.\n"
        "Update the notebook summary to concisely reflect what has been discussed so far."
        "The new transcriptions are as follows:"
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": ("\n").join(transcriptions) }
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

def get_requirements():
    """
    Retrieve the list of requirements from the Meeting Service (or other service).
    Expects a JSON response with a "requirements" field.
    """
    try:
        full_url = urljoin(MEETING_SERVICE_URL, "/api/v0/requirements")
        response = requests.get(full_url)
        if response.status_code == 200:
            data = response.json()
            requirements = data.get("requirements", "")
            print(f"Fetched requirements: {requirements}")
            return requirements
        else:
            print("Failed to fetch requirements, status:", response.status_code)
            return ""
    except Exception as e:
        print("Error fetching requirements:", e)
        return ""

class EvaluatedState(BaseModel):
    updated_state: str
    generate_code: bool
    feedback: str

def evaluate_and_maybe_update_state(current_state, requirements, notebook, transcription):
    """
    Poll the LLM with the current state, requirements, notebook summary, and latest transcription.
    """
    prompt = (
        f"Current discussion state: '{current_state}'.\n"
        f"Requirements: '{requirements}'.\n"
        f"Notebook summary: '{notebook}'.\n"
        "Based on the above, should we update the discussion state and/or trigger code generation? "
        "Respond with a valid JSON in the following format: "
        '{"update_state": "<new_state or same>", "generate_code": <true/false>}.'
    )
    messages = [
        {"role": "user", "content": prompt},
        {"role": "user", "content": f"Latest transcription: '{transcription}'.\n\n"}
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
        decision = json.loads(result)
        return decision
    except Exception as e:
        print("Error in evaluate_and_maybe_update_state:", e)
        return {"update_state": current_state, "generate_code": False}

def trigger_code_generation(current_state, requirements, notebook, transcription):
    """
    Call the external code generation service. This call is expected to have a very long timeout.
    """
    payload = {
        "state": current_state,
        "requirements": requirements,
        "notebook": notebook,
        "latest_transcription": transcription
    }
    try:
        full_url = urljoin(CODE_GENERATION_SERVICE_URL, "/api/v0/generate")
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

# -----------------------------------------------------------------------------
# Flask Endpoints
# -----------------------------------------------------------------------------

@api_v0.route("/transcription", methods=["POST"])
def receive_transcription():
    """
    Endpoint to receive a new transcription.
    1. Stores the transcription.
    2. Polls the LLM for an immediate action decision.
    3. If more than 5 transcriptions exist, updates the notebook summary.
    4. If immediate action is requested, evaluates whether to update state and/or trigger code generation.
    """
    global transcriptions, notebook_summary, current_state, code_generation_running

    data = request.get_json()
    transcription = data.get("transcription", "").strip()
    if not transcription:
        return jsonify({"status": "Error", "message": "No transcription provided."}), 400

    # Add transcription to our in-memory list
    transcriptions.append(transcription)
    print(f"Received transcription: {transcription}")

    # Decide if we need to act immediately
    immediate_action = poll_immediate_action(transcription)

    # Update notebook summary if we have more than 5 transcriptions
    if len(transcriptions) > 5:
        notebook_summary = update_notebook_summary(notebook_summary, transcriptions)
        transcriptions = [] # Clear the list after updating the summary 

    # If no immediate action, simply store the transcription and return
    if not immediate_action:
        return jsonify({"status": "OK", "message": "Transcription stored, no further action."}), 200

    # Immediate action is needed: retrieve requirements from the meeting service
    requirements = get_requirements()

    # Evaluate current state and whether to trigger code generation
    decision = evaluate_and_maybe_update_state(current_state, requirements, notebook_summary, transcription)
    new_state = decision.get("update_state", current_state)
    generate_code = decision.get("generate_code", False)

    # Update state if needed
    if new_state != current_state:
        current_state = new_state
        print(f"Updated discussion state to: {current_state}")

    # If code generation is triggered and not already running, call the code generation endpoint
    if generate_code:
        if not code_generation_running:
            code_generation_running = True
            result = trigger_code_generation(current_state, requirements, notebook_summary, transcription)
            code_generation_running = False
            return jsonify({"status": "OK", "message": "Code generation triggered.", "result": result}), 200
        else:
            return jsonify({"status": "OK", "message": "Code generation already running."}), 200

    return jsonify({"status": "OK", "message": "Transcription processed."}), 200

@api_v0.route("/transcription", methods=["GET"])
def get_transcriptions():
    """
    Optional endpoint to view the current list of transcriptions, notebook summary, and current state.
    """
    return jsonify({
        "transcriptions": transcriptions,
        "notebook_summary": notebook_summary,
        "current_state": current_state
    }), 200

if __name__ == "__main__":
    # Run the server on all interfaces at port 6000 with debugging enabled.
    app.run(host="0.0.0.0", port=SERVICE_PORT, debug=True)
