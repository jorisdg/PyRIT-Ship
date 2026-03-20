# app.py
from flask import Flask, request, jsonify
import os
import signal
from dotenv import load_dotenv
from pyritship_service import PyRITShipService, AttackNotFoundError, AttackConflictError


app = Flask(__name__)
service = PyRITShipService()


def _shutdown_handler(signum, frame):
    service.shutdown()
    raise KeyboardInterrupt

signal.signal(signal.SIGINT, _shutdown_handler)


@app.errorhandler(Exception)
def handle_exception(e):
    """Global handler — ensures all unhandled exceptions return JSON, not HTML."""
    return jsonify({"error": str(e)}), 500


@app.route('/prompt/convert')
def list_converters():
    return jsonify(service.list_converters())


@app.route('/prompt/convert/<converter_name>', methods=['POST'])
def convert(converter_name: str):
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "Missing required field: text"}), 400
    try:
        converted_text = service.convert_text(converter_name, data['text'])
        return jsonify({"converted_text": converted_text})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@app.route('/prompt/generate', methods=['POST'])
def generate_prompt():
    data = request.get_json()
    if not data or 'prompt_goal' not in data:
        return jsonify({"error": "Missing required field: prompt_goal"}), 400
    result = service.generate_prompt(data['prompt_goal'])
    return jsonify({"prompt": result})


@app.route('/prompt/score/SelfAskTrueFalseScorer', methods=['POST'])
def score():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400
    missing = [f for f in ("scoring_true", "scoring_false", "prompt_response") if f not in data]
    if missing:
        return jsonify({"error": f"Missing required field(s): {', '.join(missing)}"}), 400
    result = service.score_true_false(
        true_description=data["scoring_true"],
        false_description=data["scoring_false"],
        prompt_response=data["prompt_response"],
    )
    return jsonify(result)


@app.route('/attack/', methods=['POST'])
def start_attack():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400
    objective = data.get("objective")
    success_description = data.get("success_description")
    max_turns = data.get("max_turns", 3)

    if not objective or not success_description:
        return jsonify({"error": "objective and success_description are required"}), 400

    result = service.start_attack(objective, success_description, max_turns)
    return jsonify(result), 201


@app.route('/attack/<attack_id>/prompt', methods=['GET'])
def get_attack_prompt(attack_id: str):
    timeout = float(request.args.get("timeout", 30))
    try:
        result = service.get_attack_prompt(attack_id, timeout)
        status_code = 202 if result["status"] == "generating" else 200
        return jsonify(result), status_code
    except AttackNotFoundError:
        return jsonify({"error": "Unknown attack_id"}), 404
    except AttackConflictError as e:
        return jsonify({"error": str(e)}), 409


@app.route('/attack/<attack_id>/response', methods=['POST'])
def submit_attack_response(attack_id: str):
    data = request.get_json()
    if not data or not data.get("response"):
        return jsonify({"error": "Missing required field: response"}), 400

    try:
        result = service.submit_attack_response(attack_id, data["response"])
        return jsonify(result)
    except AttackNotFoundError:
        return jsonify({"error": "Unknown attack_id"}), 404
    except AttackConflictError as e:
        return jsonify({"error": str(e)}), 409


@app.route('/attack/<attack_id>/status', methods=['GET'])
def get_attack_status(attack_id: str):
    try:
        result = service.get_attack_status(attack_id)
        return jsonify(result)
    except AttackNotFoundError:
        return jsonify({"error": "Unknown attack_id"}), 404


if __name__ == '__main__':
    if os.environ.get("OPENAI_CHAT_ENDPOINT") is None:
        load_dotenv()

    service.authenticate_interactive()

    app.run(
        host=os.environ.get("FLASK_HOST", "127.0.0.1"),
        port=int(os.environ.get("FLASK_PORT", 5001)),
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
        threaded=False,
    )