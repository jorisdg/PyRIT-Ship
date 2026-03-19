# app.py
from flask import Flask, request, jsonify
import asyncio
import os
import time
import uuid
import inspect
import importlib
import signal
import threading
from dataclasses import dataclass
from typing import Optional, Any
from concurrent.futures import Future
from pyrit.common import default_values
from pyrit.setup import initialize_pyrit_async, IN_MEMORY
from pyrit.prompt_converter import PromptConverter
from pyrit.prompt_target import OpenAIChatTarget
from pyrit.executor.attack import PromptSendingAttack, RTASystemPromptPaths, AttackAdversarialConfig, AttackScoringConfig, RedTeamingAttack
from pyrit.score import SelfAskTrueFalseScorer, TrueFalseQuestion
from dotenv import load_dotenv
from azure.identity import InteractiveBrowserCredential, get_bearer_token_provider

from external_control_target import ExternalControlTarget


app = Flask(__name__)
chat_target = None

# Persistent asyncio event loop for running attack coroutines
_loop = asyncio.new_event_loop()
_loop_thread = threading.Thread(target=_loop.run_forever, daemon=True)
_loop_thread.start()

def _shutdown_loop(signum, frame):
    """Dispose DB connections on the event loop thread, then stop it cleanly."""
    async def _dispose():
        try:
            from pyrit.memory.central_memory import CentralMemory
            mem = CentralMemory.get_memory_instance()
            if hasattr(mem, 'dispose_engine'):
                mem.dispose_engine()
            elif hasattr(mem, '_engine'):
                mem._engine.dispose()
        except Exception:
            pass

    try:
        future = asyncio.run_coroutine_threadsafe(_dispose(), _loop)
        future.result(timeout=5)
    except Exception:
        pass

    _loop.call_soon_threadsafe(_loop.stop)
    _loop_thread.join(timeout=5)
    raise KeyboardInterrupt

signal.signal(signal.SIGINT, _shutdown_loop)


def _run_on_loop(coro):
    """Schedule a coroutine on the shared event loop and block until it completes."""
    return asyncio.run_coroutine_threadsafe(coro, _loop).result()


@dataclass
class AttackSession:
    id: str
    external_target: ExternalControlTarget
    future: Optional[Future] = None
    status: str = "starting"
    result: Optional[Any] = None
    error: Optional[str] = None
    prompt_retrieved: bool = False


# Active attack sessions keyed by UUID
_attack_sessions: dict[str, AttackSession] = {}

@app.route('/prompt/convert')
def list_converters():
    converters = PromptConverter.__subclasses__()
    converter_list = []
    for converter in converters:
        print( converter.__name__)
        params = inspect.signature(converter.__init__).parameters
        if ((len(params) == 1 and "self" in params) or (len(params) == 3 and "self" in params and "kwargs" in params and "args" in params)):
            converter_list.append(converter.__name__)
        else:
            defaults = [p for p in params if params[p].default != inspect.Parameter.empty]
            print("    params", len(params), "; defaults: ", len(defaults))
            if (len(defaults) == len(params) - 1): # all defaults but self
                converter_list.append(converter.__name__)
    return jsonify(converter_list)

@app.route('/prompt/convert/<converter_name>', methods=['POST'])
def convert(converter_name:str):
    # Extract input data from json payload
    data = request.get_json()
    input_prompt = data['text']

    # Process input data with PyRIT converters
    c = next((cls for cls in PromptConverter.__subclasses__() if cls.__name__ == converter_name), None)
    try:
        module = importlib.import_module(c.__module__)
        converter_class = getattr(module, c.__name__)
        instance = converter_class()

        converted_prompt = _run_on_loop(instance.convert_async(prompt=input_prompt, input_type="text"))
        return jsonify({"converted_text": converted_prompt.output_text})
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

@app.route('/prompt/generate', methods=['POST'])
def generate_prompt():
    # Initialize chat target
    global chat_target
    if (chat_target is None):
        chat_target = initialize_chat_target()
    
    prompt_sending_attack = PromptSendingAttack(objective_target=chat_target)
    # Extract input data from json payload
    data = request.get_json()
    prompt_goal = data['prompt_goal']

    result = _run_on_loop(prompt_sending_attack.execute_async(objective=prompt_goal)).last_response.converted_value

    return jsonify({"prompt": result})

@app.route('/prompt/score/SelfAskTrueFalseScorer', methods=['POST'])
def score():
    # Initialize chat target
    global chat_target
    if (chat_target is None):
        chat_target = initialize_chat_target()

    # Extract input data from json payload
    score_json = request.get_json()
    true_description = score_json["scoring_true"]
    false_description = score_json["scoring_false"]
    prompt_response_to_score = score_json["prompt_response"]

    scorer = SelfAskTrueFalseScorer(
        chat_target = chat_target,
        true_false_question={ 
            "category": "pyritship", 
            "true_description": true_description, 
            "false_description": false_description
            }
    )

    scored_response = _run_on_loop(scorer.score_text_async(text=prompt_response_to_score))[0]
    return jsonify(
         {
            "scoring_text": str(scored_response.get_value()),
            "scoring_metadata": scored_response.score_metadata,
            "scoring_rationale": scored_response.score_rationale
         }
    )
    
def _get_session_or_404(attack_id: str):
    session = _attack_sessions.get(attack_id)
    if not session:
        return None
    # Sync status from future
    if session.future and session.future.done():
        try:
            session.result = session.future.result()
            session.status = "completed"
        except Exception as e:
            session.error = str(e)
            session.status = "error"
    return session


@app.route('/attack/', methods=['POST'])
def start_attack():
    data = request.get_json()
    objective = data.get("objective")
    success_description = data.get("success_description")
    max_turns = data.get("max_turns", 3)

    if not objective or not success_description:
        return jsonify({"error": "objective and success_description are required"}), 400

    attack_id = str(uuid.uuid4())
    session = AttackSession(id=attack_id, external_target=None)
    _attack_sessions[attack_id] = session

    # Schedule the attack coroutine on the persistent event loop
    # All PyRIT init (including ExternalControlTarget) happens on the event loop thread
    session.future = asyncio.run_coroutine_threadsafe(
        _run_attack(objective, success_description, max_turns, session), _loop
    )

    return jsonify({"attack_id": attack_id, "status": "starting"}), 201


@app.route('/attack/<attack_id>/prompt', methods=['GET'])
def get_attack_prompt(attack_id: str):
    session = _get_session_or_404(attack_id)
    if not session:
        return jsonify({"error": "Unknown attack_id"}), 404

    if session.status == "completed":
        _attack_sessions.pop(attack_id, None)
        return jsonify({"attack_id": attack_id, "status": "completed", "result": str(session.result)})

    if session.status == "error":
        _attack_sessions.pop(attack_id, None)
        return jsonify({"attack_id": attack_id, "status": "error", "error": session.error})

    if session.prompt_retrieved and session.external_target and session.external_target.is_waiting():
        return jsonify({"error": "Prompt already retrieved, submit response first"}), 409

    # Block up to timeout waiting for a prompt
    timeout = float(request.args.get("timeout", 30))
    deadline = time.time() + timeout
    while time.time() < deadline:
        if session.external_target:
            prompt = session.external_target.get_current_prompt()
            if prompt:
                session.status = "waiting_for_response"
                session.prompt_retrieved = True
                text = prompt.message_pieces[0].converted_value
                return jsonify({"attack_id": attack_id, "status": "waiting_for_response", "prompt": text})

        # Check if attack finished while we were waiting
        if session.future and session.future.done():
            session = _get_session_or_404(attack_id)
            if session.status in ("completed", "error"):
                _attack_sessions.pop(attack_id, None)
                resp = {"attack_id": attack_id, "status": session.status}
                if session.result:
                    resp["result"] = str(session.result)
                if session.error:
                    resp["error"] = session.error
                return jsonify(resp)

        time.sleep(0.1)

    return jsonify({"attack_id": attack_id, "status": "generating", "message": "Prompt not ready yet, try again"}), 202


@app.route('/attack/<attack_id>/response', methods=['POST'])
def submit_attack_response(attack_id: str):
    session = _get_session_or_404(attack_id)
    if not session:
        return jsonify({"error": "Unknown attack_id"}), 404

    if session.status == "completed":
        return jsonify({"attack_id": attack_id, "status": "completed", "result": str(session.result)})

    if session.status == "error":
        return jsonify({"attack_id": attack_id, "status": "error", "error": session.error})

    if not session.prompt_retrieved or not session.external_target or not session.external_target.is_waiting():
        return jsonify({"error": "No prompt outstanding"}), 409

    data = request.get_json()
    response_text = data.get("response")
    if not response_text:
        return jsonify({"error": "response is required"}), 400

    session.external_target.submit_response(response_text)
    session.prompt_retrieved = False
    session.status = "processing_response"

    return jsonify({"attack_id": attack_id, "status": "processing_response"})


@app.route('/attack/<attack_id>/status', methods=['GET'])
def get_attack_status(attack_id: str):
    session = _get_session_or_404(attack_id)
    if not session:
        return jsonify({"error": "Unknown attack_id"}), 404

    response = {"attack_id": attack_id, "status": session.status}
    if session.status == "completed":
        response["result"] = str(session.result)
        _attack_sessions.pop(attack_id, None)
    if session.status == "error":
        response["error"] = session.error
        _attack_sessions.pop(attack_id, None)

    return jsonify(response)


async def _run_attack(objective: str, success_description: str, max_turns: int, session: AttackSession):
    """Wrapper coroutine that runs the attack on the event loop thread."""
    global chat_target

    await initialize_pyrit_async(memory_db_type=IN_MEMORY)

    if chat_target is None:
        chat_target = _build_chat_target()

    # Create ExternalControlTarget on the event loop thread (requires PyRIT memory)
    session.external_target = ExternalControlTarget()

    adversarial_config = AttackAdversarialConfig(
        target=chat_target,
        system_prompt_path=RTASystemPromptPaths.TEXT_GENERATION.value,
    )

    scoring_config = AttackScoringConfig(
        objective_scorer=SelfAskTrueFalseScorer(
            chat_target=chat_target,
            true_false_question=TrueFalseQuestion(true_description=success_description),
        ),
    )

    red_teaming_attack = RedTeamingAttack(
        objective_target=session.external_target,
        attack_adversarial_config=adversarial_config,
        attack_scoring_config=scoring_config,
        max_turns=max_turns,
    )

    return await red_teaming_attack.execute_async(objective=objective)


def _build_chat_target():
    """Build the OpenAI chat target instance."""
    endpoint = os.environ.get("OPENAI_CHAT_ENDPOINT", "")
    api_key = os.environ.get("OPENAI_CHAT_KEY", "")

    if not api_key and "azure.com/" in endpoint:
        token_provider = get_bearer_token_provider(
            InteractiveBrowserCredential(),
            "https://cognitiveservices.azure.com/.default",
        )
        api_key = token_provider

    return OpenAIChatTarget(
        model_name=os.environ.get("OPENAI_CHAT_MODEL_NAME"),
        endpoint=endpoint,
        api_key=api_key,
    )

def initialize_chat_target():
    """Initialize PyRIT memory and create the OpenAI chat target, all on the event loop thread."""
    _run_on_loop(initialize_pyrit_async(memory_db_type=IN_MEMORY))
    return _build_chat_target()

if __name__ == '__main__':
    if os.environ.get("OPENAI_CHAT_ENDPOINT") is None:
        load_dotenv()
    app.run(
        host=os.environ.get("FLASK_HOST", "127.0.0.1"),
        port=int(os.environ.get("FLASK_PORT", 5001)),
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
        threaded=False,
    )