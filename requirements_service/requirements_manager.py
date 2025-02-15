import os
import uuid
from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)
api = Blueprint("api", __name__)

# -----------------------------------------------------------------------------
# Environment & LLM Configuration
# -----------------------------------------------------------------------------
SERVICE_PORT = int(os.environ.get("SERVICE_PORT", 8081))
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai").lower()  # "openrouter", "openai" or "ollama"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OLLAMA_URL = os.environ.get("OLLAMA_URL")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL")

# Choose the model based on the provider
CHOSEN_MODEL = (
    OPENAI_MODEL
    if LLM_PROVIDER == "openai"
    else OPENROUTER_MODEL
    if LLM_PROVIDER == "openrouter"
    else OLLAMA_MODEL
)

# -----------------------------------------------------------------------------
# LLM Client Setup
# -----------------------------------------------------------------------------
def get_llm_client():
    """
    Returns an LLM client configured for the chosen provider.
    Note: This example assumes that the 'openai' package can be used
    for all providers by adjusting the base_url and api_key.
    """
    if LLM_PROVIDER == "openrouter":
        return OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )
    elif LLM_PROVIDER == "openai":
        return OpenAI(
            api_key=OPENAI_API_KEY,
        )
    elif LLM_PROVIDER == "ollama":
        return OpenAI(
            base_url=OLLAMA_URL,
            api_key="ollama",  # The key is required by the interface, even if unused
        )
    else:
        raise ValueError("Unsupported LLM Provider")

llm_client = get_llm_client()

# -----------------------------------------------------------------------------
# In-Memory Meeting Storage
# -----------------------------------------------------------------------------
# Each meeting will be stored as:
# {
#   "requirements": "<current requirements text>",
#   "pending_transcriptions": [ ... ]
# }
meetings = {}

# How many transcriptions trigger a requirements update?
REQUIREMENT_UPDATE_INTERVAL = int(os.environ.get("REQUIREMENT_UPDATE_INTERVAL", 5))

# -----------------------------------------------------------------------------
# LLM Helper Function: Update Requirements List
# -----------------------------------------------------------------------------
def update_requirements_list(current_requirements, transcriptions):
    """
    Given the current requirements and a list of new meeting transcriptions,
    call the LLM to update (and possibly evolve) the requirements.
    The prompt instructs the LLM to return a bullet list of requirements.
    """
    system_prompt = (
        "You are a requirements management assistant for a software project. "
        "The project requirements evolve as the meeting discussion progresses. "
        "Given the current list of requirements and the new meeting transcriptions, "
        "update the requirements list. If any requirement has changed, be sure to modify it. "
        "Return the updated requirements as a bullet list with each requirement on a new line. "
        "Do not include any additional commentary."
    )
    user_prompt = (
        f"Current requirements:\n{current_requirements}\n\n"
        "New meeting transcriptions:\n" + "\n".join(transcriptions)
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    try:
        response = llm_client.chat.completions.create(
            model=CHOSEN_MODEL,
            messages=messages,
            max_tokens=200,
        )
        updated_requirements = response.choices[0].message.content.strip()
        print(f"Updated requirements:\n{updated_requirements}")
        return updated_requirements
    except Exception as e:
        print("Error updating requirements:", e)
        # If there is an error, return the current requirements unchanged.
        return current_requirements

# -----------------------------------------------------------------------------
# Flask Endpoints
# -----------------------------------------------------------------------------

@api.route("/meeting", methods=["POST"])
def create_meeting():
    """
    Creates a new meeting and returns a unique meeting ID.
    """
    meeting_id = str(uuid.uuid4())
    meetings[meeting_id] = {
        "requirements": "",
        "pending_transcriptions": [],
    }
    print(f"Created new meeting with ID: {meeting_id}")
    return jsonify({"meeting_id": meeting_id}), 201

@api.route("/meeting/<meeting_id>/transcription", methods=["POST"])
def receive_transcription(meeting_id):
    """
    Receives a new transcription for a given meeting.
    The transcription is added to the meeting's pending transcriptions list.
    Once the count reaches the update threshold, the LLM is called to update
    the requirements list, and the pending transcriptions are cleared.
    """
    if meeting_id not in meetings:
        return jsonify({"status": "Error", "message": "Meeting ID not found."}), 404

    data = request.get_json()
    transcription = data.get("transcription", "").strip()
    if not transcription:
        return jsonify({"status": "Error", "message": "No transcription provided."}), 400

    meeting = meetings[meeting_id]
    meeting["pending_transcriptions"].append(transcription)
    print(f"Received transcription for meeting {meeting_id}: {transcription}")

    if len(meeting["pending_transcriptions"]) >= REQUIREMENT_UPDATE_INTERVAL:
        update_requirements(meeting_id)
        return jsonify({
            "status": "OK",
            "message": "Requirements updated."
        }), 200

    return jsonify({"status": "OK", "message": "Transcription received."}), 200

def update_requirements(meeting_id):
    meeting = meetings[meeting_id]
    current_requirements = meeting["requirements"]
    new_transcriptions = meeting["pending_transcriptions"]
    updated_requirements = update_requirements_list(current_requirements, new_transcriptions)
    meeting["requirements"] = updated_requirements
    meeting["pending_transcriptions"] = []


@api.route("/meeting/<meeting_id>/requirements", methods=["GET"])
def get_requirements(meeting_id):
    """
    Returns the current requirements list for the specified meeting.
    """
    if meeting_id not in meetings:
        return jsonify({"status": "Error", "message": "Meeting ID not found."}), 404

    update_requirements(meeting_id)
    meeting = meetings[meeting_id]
    return jsonify({
        "status": "OK",
        "requirements": meeting["requirements"]
    }), 200

# Register the blueprint with a URL prefix
app.register_blueprint(api, url_prefix="/api/v0")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=SERVICE_PORT, debug=True)
