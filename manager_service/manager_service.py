import os
import json
import requests
from openai import OpenAI
from fastapi import FastAPI, Request, HTTPException, APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from enum import Enum
from dotenv import load_dotenv
import asyncio

import uvicorn

load_dotenv()

app = FastAPI()
router = APIRouter(prefix="/api/v0")

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
current_state = DiscussionState.CONCEPTUALIZATION
transcriptions = []             # List of received transcription messages
requirements = ""               # List of software requirements
notebook_summary = ""           # Summary of the discussion (the “notebook”)
code_generation_running = False  # Flag to indicate if a code generation job is running
deployment_url = ""             # URL where the generated code will be deployed

# Environment configuration for LLM providers and service URLs
SERVICE_PORT = os.environ.get("MANAGER_SERVICE_PORT")
LLM_PROVIDER = os.environ.get("LLM_PROVIDER") 
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL")
OLLAMA_URL = os.environ.get("OLLAMA_URL")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL")
VOICE_SERVICE_URL = os.environ.get("VOICE_SERVICE_URL")
MEETING_SERVICE_URL = os.environ.get("MEETING_SERVICE_URL")
CODE_GENERATION_SERVICE_URL = os.environ.get("CODE_GENERATION_SERVICE_URL")

# Choose the model based on the provider
CHOSEN_MODEL = (
    OPENAI_MODEL if LLM_PROVIDER == "openai"
    else OPENROUTER_MODEL if LLM_PROVIDER == "openrouter"
    else OLLAMA_MODEL
)

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

def poll_immediate_action(transcription: str) -> bool:
    """
    Poll the LLM to decide if immediate action is needed based on the latest transcription.
    The prompt asks for a True/False answer.
    """
    system_prompt = (
        "You are a meeting assistant for a software development meeting focused on creating new software."
        "Analyze the provided transcription snippet and determine if the content indicates that an immediate action is required."
        "Possible reasons to take action include updating meeting minutes, updating current state of discussion or generating code."
        "Return your answer as a valid JSON with a single field 'take_action' set to true or false. Do not include any extra commentary."
    )
    user_prompt = f"Transcription snippet: '{transcription}'"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Latest transcription: {user_prompt}"},
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

def update_notebook_summary(current_notebook: str, transcriptions: list) -> str:
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
            max_tokens=1000,
        )
        new_summary = response.choices[0].message.content.strip()
        print(f"Updated notebook summary: {new_summary}")
        return new_summary
    except Exception as e:
        print("Error in update_notebook_summary:", e)
        return current_notebook

def get_requirements(meeting_id: str) -> str:
    """
    Retrieve the list of requirements from the Meeting Service (or other service).
    Expects a JSON response with a "requirements" field.
    """
    try:
        full_url = MEETING_SERVICE_URL + f"/meeting/{meeting_id}/requirements"
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

def evaluate_and_maybe_update_state(current_state: DiscussionState, requirements: str, notebook: str, transcription: str):
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
        Respond with a valid JSON object containing an 'updated_state' key (with one of the allowed enum values (it can be the same if no change is needed)),
        a boolean 'generate_code' flag, along with 'feedback'.
        Respond only with valid JSON. Do not write an introduction or summary.
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
        print(response)
        result = response.choices[0].message.parsed
        print(f"State evaluation LLM response: {result}")
        return result.updated_state, result.generate_code, result.feedback
    except Exception as e:
        print("Error in evaluate_and_maybe_update_state:", e)
        return current_state, False, ""

def trigger_code_generation(requirements: str):
    """
    Call the external code generation service. This call is expected to have a very long timeout.
    """
    payload = {
        "prompt": requirements,
    }
    try:
        full_url = CODE_GENERATION_SERVICE_URL + "/prompt"
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

@router.post("/meeting/{meeting_id}/transcription")
async def receive_transcription(meeting_id: str, request: Request):
    """
    Endpoint to receive a new transcription.
    1. Stores the transcription.
    2. Polls the LLM for an immediate action decision.
    3. If more than 5 transcriptions exist, updates the notebook summary.
    4. If immediate action is requested, evaluates whether to update state and/or trigger code generation.
    """
    global transcriptions, notebook_summary, current_state, code_generation_running, requirements, deployment_url

    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from e

    transcription = data.get("transcription", "").strip()
    if not transcription:
        raise HTTPException(status_code=400, detail="No transcription provided.")

    # Add transcription to our in-memory list
    transcriptions.append(transcription)
    print(f"Received transcription: {transcription}")
    # Publish transcription via SSE (using our custom announcer)

    # Decide if we need to act immediately
    immediate_action = poll_immediate_action(transcription)

    # Update notebook summary if we have more than 5 transcriptions
    if len(transcriptions) % 5 == 0:
        notebook_summary = update_notebook_summary(notebook_summary, transcriptions)
        transcriptions = transcriptions[-5:]  # Keep only the last 5 transcriptions

    # If no immediate action, simply store the transcription and return
    if not immediate_action:
        return JSONResponse(content={"status": "OK", "message": "Transcription stored, no further action."})


    # Immediate action is needed: retrieve requirements from the meeting service
    requirements = get_requirements(meeting_id)
    new_state, generate_code, feedback = evaluate_and_maybe_update_state(
        current_state, requirements, notebook_summary, transcription
    )

    print(f"LLM feedback: {feedback}")

    if new_state != current_state:
        current_state = new_state
        print(f"Updated discussion state to: {current_state}")

    if generate_code:
        if not code_generation_running:
            code_generation_running = True
            result = trigger_code_generation(requirements)
            deployment_url = result.get("frontend_url", "")
            code_generation_running = False
            return JSONResponse(content={
                "status": "OK",
                "message": "Code generation triggered.",
                "result": result
            })
        else:
            return JSONResponse(content={
                "status": "OK",
                "message": "Code generation already running."
            })

    return JSONResponse(content={"status": "OK", "message": "Transcription processed."})

@router.get("/sse", status_code=200)
async def sse_stream():
    """
    SSE stream endpoint to continuously send the current state.
    """
    async def event_stream():
        while True:
            data = {
                "transcriptions": transcriptions,
                "notebook_summary": notebook_summary,
                "current_state": current_state.value,
                "code_generation_running": code_generation_running,
                "requirements": requirements,
                "deployment_url": deployment_url,
            }
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(1)
    return StreamingResponse(event_stream(), media_type="text/event-stream")

app.include_router(router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    print(f"Starting Manager Service on port {SERVICE_PORT}")
    uvicorn.run("manager_service:app", host="0.0.0.0", port=int(SERVICE_PORT), reload=False)
