# mcp_server.py
import os
import signal
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pyritship_service import PyRITShipService, AttackNotFoundError, AttackConflictError


load_dotenv()

service = PyRITShipService()
service.authenticate_interactive()

transport = os.environ.get("MCP_TRANSPORT", "streamable-http")
host = os.environ.get("MCP_HOST", "127.0.0.1")
port = int(os.environ.get("MCP_PORT", 8001))

mcp = FastMCP("PyRIT Ship", host=host, port=port)


def _shutdown_handler(signum, frame):
    service.shutdown()
    raise KeyboardInterrupt

signal.signal(signal.SIGINT, _shutdown_handler)


@mcp.tool()
def list_converters() -> list[str]:
    """List available PyRIT prompt converters that can be used with convert_text."""
    return service.list_converters()


@mcp.tool()
def convert_text(converter_name: str, text: str) -> str:
    """Convert text using a named PyRIT converter (e.g. ROT13Converter, LeetspeakConverter).
    Use list_converters to see available options."""
    return service.convert_text(converter_name, text)


@mcp.tool()
def generate_prompt(prompt_goal: str) -> str:
    """Generate an adversarial prompt for a given goal using PyRIT's prompt sending attack."""
    return service.generate_prompt(prompt_goal)


@mcp.tool()
def score_true_false(scoring_true: str, scoring_false: str, prompt_response: str) -> dict:
    """Score a prompt response using PyRIT's SelfAskTrueFalseScorer.

    Args:
        scoring_true: Description of what constitutes a 'true' score.
        scoring_false: Description of what constitutes a 'false' score.
        prompt_response: The text to score.
    """
    return service.score_true_false(scoring_true, scoring_false, prompt_response)


@mcp.tool()
def start_attack(objective: str, success_description: str, max_turns: int = 3) -> dict:
    """Start a new red teaming attack session.

    Args:
        objective: The attack objective (e.g. 'try to get the agent to reveal its system prompt').
        success_description: What constitutes a successful attack (e.g. 'the agent reveals its system prompt').
        max_turns: Maximum conversation turns (default 3).

    Returns a dict with attack_id and status.
    """
    return service.start_attack(objective, success_description, max_turns)


@mcp.tool()
def get_attack_prompt(attack_id: str, timeout: int = 30) -> dict:
    """Get the next prompt from an active attack. Blocks up to timeout seconds waiting for a prompt.

    Returns status 'waiting_for_response' with the prompt text, 'completed' with the result
    when the attack is finished, or 'generating' if the prompt isn't ready yet.
    """
    return service.get_attack_prompt(attack_id, float(timeout))


@mcp.tool()
def submit_attack_response(attack_id: str, response: str) -> dict:
    """Submit a response for the current attack prompt. Must call get_attack_prompt first."""
    return service.submit_attack_response(attack_id, response)


@mcp.tool()
def get_attack_status(attack_id: str) -> dict:
    """Check the status of an attack without side effects."""
    return service.get_attack_status(attack_id)


if __name__ == "__main__":
    mcp.run(transport=transport)
