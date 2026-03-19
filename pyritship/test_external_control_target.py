# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import asyncio
import threading
from typing import MutableSequence

import pytest
from unit.mocks import get_sample_conversations

from pyrit.models import Message, MessagePiece
from pyrit.prompt_target import ExternalControlTarget


@pytest.fixture
def sample_entries() -> MutableSequence[MessagePiece]:
    conversations = get_sample_conversations()
    return Message.flatten_to_message_pieces(conversations)


@pytest.fixture
def external_target() -> ExternalControlTarget:
    return ExternalControlTarget()


@pytest.mark.asyncio
async def test_get_current_prompt_returns_none_initially(external_target: ExternalControlTarget):
    """Test that get_current_prompt returns None when no prompt is waiting."""
    assert external_target.get_current_prompt() is None


@pytest.mark.asyncio
async def test_is_waiting_false_initially(external_target: ExternalControlTarget):
    """Test that is_waiting returns False initially."""
    assert external_target.is_waiting() is False


@pytest.mark.asyncio
async def test_send_prompt_stores_message(external_target: ExternalControlTarget, sample_entries: MutableSequence[MessagePiece]):
    """Test that send_prompt_async stores the message for external retrieval."""
    request = sample_entries[0]
    request.converted_value = "Test prompt"
    message = Message(message_pieces=[request])

    # Start send_prompt_async in background
    async def send():
        await external_target.send_prompt_async(message=message)

    task = asyncio.create_task(send())

    # Give it time to store the prompt
    await asyncio.sleep(0.1)

    # Verify prompt is stored
    stored_prompt = external_target.get_current_prompt()
    assert stored_prompt is not None
    assert stored_prompt.message_pieces[0].converted_value == "Test prompt"

    # Clean up by submitting response
    external_target.submit_response("response")
    await task


@pytest.mark.asyncio
async def test_is_waiting_true_during_wait(external_target: ExternalControlTarget, sample_entries: MutableSequence[MessagePiece]):
    """Test that is_waiting returns True while waiting for response."""
    request = sample_entries[0]
    request.converted_value = "Test prompt"
    message = Message(message_pieces=[request])

    # Start send_prompt_async in background
    async def send():
        await external_target.send_prompt_async(message=message)

    task = asyncio.create_task(send())

    # Give it time to start waiting
    await asyncio.sleep(0.1)

    # Verify waiting state
    assert external_target.is_waiting() is True

    # Clean up
    external_target.submit_response("response")
    await task


@pytest.mark.asyncio
async def test_submit_response_unblocks_executor(external_target: ExternalControlTarget, sample_entries: MutableSequence[MessagePiece]):
    """Test that submit_response unblocks send_prompt_async."""
    request = sample_entries[0]
    request.converted_value = "Test prompt"
    message = Message(message_pieces=[request])

    response_text = "External response"

    # Start send_prompt_async in background
    async def send():
        return await external_target.send_prompt_async(message=message)

    task = asyncio.create_task(send())

    # Give it time to start waiting
    await asyncio.sleep(0.1)

    # Submit response
    external_target.submit_response(response_text)

    # Wait for task to complete
    result = await task

    # Verify response
    assert len(result) == 1
    assert result[0].message_pieces[0].converted_value == response_text


@pytest.mark.asyncio
async def test_response_wrapped_in_message(external_target: ExternalControlTarget, sample_entries: MutableSequence[MessagePiece]):
    """Test that raw string response is properly wrapped in Message object."""
    request = sample_entries[0]
    request.converted_value = "Test prompt"
    message = Message(message_pieces=[request])

    response_text = "This is the response"

    # Start send_prompt_async in background
    async def send():
        return await external_target.send_prompt_async(message=message)

    task = asyncio.create_task(send())
    await asyncio.sleep(0.1)

    # Submit raw string response
    external_target.submit_response(response_text)
    result = await task

    # Verify result is a proper Message
    assert len(result) == 1
    assert isinstance(result[0], Message)
    assert len(result[0].message_pieces) == 1
    assert result[0].message_pieces[0].role == "assistant"
    assert result[0].message_pieces[0].converted_value == response_text


@pytest.mark.asyncio
async def test_state_cleared_after_response(external_target: ExternalControlTarget, sample_entries: MutableSequence[MessagePiece]):
    """Test that state is cleared after response is received."""
    request = sample_entries[0]
    request.converted_value = "Test prompt"
    message = Message(message_pieces=[request])

    async def send():
        return await external_target.send_prompt_async(message=message)

    task = asyncio.create_task(send())
    await asyncio.sleep(0.1)

    # Verify state during wait
    assert external_target.is_waiting() is True
    assert external_target.get_current_prompt() is not None

    # Submit response
    external_target.submit_response("response")
    await task

    # Verify state is cleared
    assert external_target.is_waiting() is False
    assert external_target.get_current_prompt() is None


@pytest.mark.asyncio
async def test_multiple_sequential_prompts(external_target: ExternalControlTarget, sample_entries: MutableSequence[MessagePiece]):
    """Test multiple sequential prompt/response cycles."""
    for i in range(3):
        request = sample_entries[0]
        request.converted_value = f"Prompt {i}"
        message = Message(message_pieces=[request])

        async def send():
            return await external_target.send_prompt_async(message=message)

        task = asyncio.create_task(send())
        await asyncio.sleep(0.1)

        # Verify correct prompt is stored
        stored = external_target.get_current_prompt()
        assert stored.message_pieces[0].converted_value == f"Prompt {i}"

        # Submit response
        external_target.submit_response(f"Response {i}")
        result = await task

        # Verify response
        assert result[0].message_pieces[0].converted_value == f"Response {i}"


@pytest.mark.asyncio
async def test_validate_request_with_empty_message():
    """Test that validation fails with empty message."""
    target = ExternalControlTarget()

    with pytest.raises(ValueError, match="Message must contain at least one message piece"):
        await target.send_prompt_async(message=Message(message_pieces=[]))


@pytest.mark.asyncio
async def test_cleanup_target(external_target: ExternalControlTarget, sample_entries: MutableSequence[MessagePiece]):
    """Test that cleanup_target clears state."""
    request = sample_entries[0]
    request.converted_value = "Test prompt"
    message = Message(message_pieces=[request])

    # Start send and add response to queue
    async def send():
        return await external_target.send_prompt_async(message=message)

    task = asyncio.create_task(send())
    await asyncio.sleep(0.1)

    external_target.submit_response("response")
    await task

    # Add extra item to queue
    external_target.submit_response("extra")

    # Cleanup
    await external_target.cleanup_target()

    # Verify state is cleared
    assert external_target.get_current_prompt() is None
    assert external_target.is_waiting() is False
    assert external_target._response_queue.empty()


@pytest.mark.asyncio
async def test_thread_safety_multiple_get_calls(external_target: ExternalControlTarget, sample_entries: MutableSequence[MessagePiece]):
    """Test that get_current_prompt is thread-safe when called from multiple threads."""
    request = sample_entries[0]
    request.converted_value = "Thread safety test"
    message = Message(message_pieces=[request])

    results = []

    async def send():
        return await external_target.send_prompt_async(message=message)

    task = asyncio.create_task(send())
    await asyncio.sleep(0.1)

    # Call get_current_prompt from multiple threads
    def get_prompt():
        prompt = external_target.get_current_prompt()
        if prompt:
            results.append(prompt.message_pieces[0].converted_value)

    threads = [threading.Thread(target=get_prompt) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # All threads should get the same prompt
    assert len(results) == 10
    assert all(r == "Thread safety test" for r in results)

    # Clean up
    external_target.submit_response("response")
    await task


@pytest.mark.asyncio
async def test_thread_safety_submit_response(external_target: ExternalControlTarget, sample_entries: MutableSequence[MessagePiece]):
    """Test that submit_response is thread-safe when called from multiple threads."""
    request = sample_entries[0]
    request.converted_value = "Test prompt"
    message = Message(message_pieces=[request])

    async def send():
        return await external_target.send_prompt_async(message=message)

    task = asyncio.create_task(send())
    await asyncio.sleep(0.1)

    # Submit from main thread (first one wins)
    external_target.submit_response("main thread response")

    # Try submitting from other threads (these will be ignored/queued)
    def submit():
        external_target.submit_response("thread response")

    threads = [threading.Thread(target=submit) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # Wait for task
    result = await task

    # First response should be used
    assert result[0].message_pieces[0].converted_value == "main thread response"

    # Cleanup extra responses in queue
    await external_target.cleanup_target()


@pytest.mark.asyncio
async def test_disconnected_polling_pattern(external_target: ExternalControlTarget, sample_entries: MutableSequence[MessagePiece]):
    """Test the disconnected polling pattern (simulating Flask API usage)."""
    request = sample_entries[0]
    request.converted_value = "API test prompt"
    message = Message(message_pieces=[request])

    # Simulate executor starting
    async def send():
        return await external_target.send_prompt_async(message=message)

    executor_task = asyncio.create_task(send())

    # Simulate external program polling (like Flask GET /next-prompt)
    await asyncio.sleep(0.1)
    prompt = external_target.get_current_prompt()
    assert prompt is not None
    assert prompt.message_pieces[0].converted_value == "API test prompt"

    # Simulate external program doing work (minutes could pass here)
    await asyncio.sleep(0.2)

    # External program still sees same prompt
    prompt_again = external_target.get_current_prompt()
    assert prompt_again is not None
    assert prompt_again.message_pieces[0].converted_value == "API test prompt"

    # Simulate external program submitting response (like Flask POST /submit-response)
    external_target.submit_response("API response after processing")

    # Executor should complete
    result = await executor_task

    # Verify final state
    assert result[0].message_pieces[0].converted_value == "API response after processing"
    assert external_target.is_waiting() is False
    assert external_target.get_current_prompt() is None
