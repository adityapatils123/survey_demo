# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import json
import asyncio
import base64
import warnings
import logging

from pathlib import Path
from dotenv import load_dotenv

from google.genai.types import (
    Part,
    Content,
    Blob,
)

from google.adk.runners import InMemoryRunner, Runner
from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig
from google.genai import types

from typing import Any, Dict
from pydantic import BaseModel

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.websockets import WebSocketDisconnect

from form_agent.agent import form_assistant_agent
from form_agent.survey_data import SURVEY_DATA, get_next_step, validate_answer, get_filtered_survey_data
from database import get_database
from retry_utils import retry, retry_async as retry_func

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", message="there are non-text parts in the response")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Reduce ADK logging verbosity (suppress "non-text parts" warnings)
logging.getLogger('google.genai').setLevel(logging.ERROR)
logging.getLogger('google.adk').setLevel(logging.ERROR)

#
# ADK Streaming
#

# Load Gemini API Key
load_dotenv()

APP_NAME = "Medical Survey Form"

# Initialize database
db = get_database()
logger.info("Database initialized for session persistence")



async def agent_to_client_messaging(websocket, initial_live_events, session, is_audio, runner, live_request_queue, user_id):
    """Agent to client communication with automatic retry and session persistence"""
    # Accumulators for full transcripts
    full_input_transcript = ""
    full_output_transcript = ""
    last_known_step = session.state.get("current_step", "S1")
    last_saved_state = None  # Track last saved state to avoid unnecessary saves
    last_save_time = asyncio.get_event_loop().time()
    SAVE_INTERVAL = 30.0  # Save session every 30 seconds as backup
    
    # Configuration for retries
    if is_audio:
        modalities = ["AUDIO"]
    else:
        modalities = ["TEXT"]
    
    run_config = RunConfig(
        response_modalities=modalities,
        output_audio_transcription=types.AudioTranscriptionConfig() if is_audio else None,
        input_audio_transcription=types.AudioTranscriptionConfig() if is_audio else None,
    )
    
    live_events = initial_live_events

    while True:
        try:
            async for event in live_events:
                # Check for input transcription (transcript of user's audio speech)
                if event.input_transcription:
                    # input_transcription might be an object with a 'text' attribute
                    if hasattr(event.input_transcription, 'text'):
                        input_text = event.input_transcription.text
                    else:
                        input_text = str(event.input_transcription)
                    
                    if input_text:
                        # Accumulate full transcript
                        full_input_transcript += input_text
                        
                        message = {
                            "mime_type": "text/plain",
                            "data": input_text,
                            "partial": event.partial,
                            "is_input_transcript": True
                        }
                        await websocket.send_text(json.dumps(message))
                        print(f"[USER INPUT TRANSCRIPT]: {input_text}")
            
                # Check for output transcription (transcript of agent's audio speech)
                if event.output_transcription:
                    # output_transcription might be an object with a 'text' attribute
                    if hasattr(event.output_transcription, 'text'):
                        transcript_text = event.output_transcription.text
                    else:
                        transcript_text = str(event.output_transcription)
                    
                    if transcript_text:
                        # Accumulate full transcript
                        full_output_transcript += transcript_text
                        
                        message = {
                            "mime_type": "text/plain",
                            "data": transcript_text,
                            "partial": event.partial,
                            "is_output_transcript": True
                        }
                        await websocket.send_text(json.dumps(message))
                        print(f"[AGENT OUTPUT TRANSCRIPT]: {transcript_text}")

                # If the turn complete or interrupted
                if event.turn_complete or event.interrupted:
                    message = {
                        "turn_complete": event.turn_complete,
                        "interrupted": event.interrupted,
                    }
                    await websocket.send_text(json.dumps(message))
                    # Fallback: if turn finished and step changed (e.g. form save_answer), ensure navigation is sent
                    if event.turn_complete and not event.interrupted:
                        cs = session.state.get("current_step")
                        if cs and cs != last_known_step:
                            last_known_step = cs
                            nav_message = {
                                "type": "navigation",
                                "step": cs,
                                "answers": session.state.get("answers", {}),
                                "step_history": session.state.get("step_history", []),
                            }
                            await websocket.send_text(json.dumps(nav_message))
                            print(f"[SERVER -> CLIENT] Navigation update (turn_complete): {cs}")

                # Check for state changes (Agent drove navigation)
                current_step_in_state = session.state.get("current_step")
                if current_step_in_state and current_step_in_state != last_known_step:
                    last_known_step = current_step_in_state
                    # Send navigation command to client (includes step_history for form back-support)
                    nav_message = {
                        "type": "navigation",
                        "step": current_step_in_state,
                        "answers": session.state.get("answers", {}),
                        "step_history": session.state.get("step_history", [])
                    }
                    await websocket.send_text(json.dumps(nav_message))
                    print(f"[SERVER -> CLIENT] Navigation update: {current_step_in_state}")
                    
                    # Persist session state to database with retry logic
                    await save_session_state_async(
                        user_id=user_id,
                        current_step=current_step_in_state,
                        answers=session.state.get("answers", {}),
                        step_history=session.state.get("step_history", []),
                        is_audio_mode=is_audio
                    )
                    last_save_time = asyncio.get_event_loop().time()
                    
                    # Reset transcripts for next turn
                    full_input_transcript = ""
                    full_output_transcript = ""
                    
                    # Also check for answer changes (even if step hasn't changed, answers might have)
                    # This helps with real-time sync when user manually changes answers
                    current_answers = session.state.get("answers", {})
                    if current_answers:
                        # Send periodic state updates to ensure UI stays in sync
                        # (This is handled by navigation messages, but we can add explicit answer updates if needed)
                        pass

                # Read the Content and its first Part
                part: Part = (
                    event.content and event.content.parts and event.content.parts[0]
                )
                if not part:
                    continue

                # If it's audio, send Base64 encoded audio data
                is_audio_part = part.inline_data and part.inline_data.mime_type.startswith("audio/pcm")
                if is_audio_part:
                    audio_data = part.inline_data and part.inline_data.data
                    if audio_data:
                        message = {
                            "mime_type": "audio/pcm",
                            "data": base64.b64encode(audio_data).decode("ascii")
                        }
                        await websocket.send_text(json.dumps(message))
                        print(f"[AGENT TO CLIENT]: audio/pcm: {len(audio_data)} bytes.")
                        continue

                # If it's text (partial or complete), send it
                if part.text:
                    message = {
                        "mime_type": "text/plain",
                        "data": part.text,
                        "partial": event.partial,
                        "is_transcript": False  # This is regular text, not transcript
                    }
                    await websocket.send_text(json.dumps(message))
                    print(f"[AGENT TO CLIENT]: text/plain: {part.text[:100]}...")
                
                # Periodic session save (every SAVE_INTERVAL seconds)
                current_time = asyncio.get_event_loop().time()
                if current_time - last_save_time >= SAVE_INTERVAL:
                    try:
                        await save_session_state_async(
                            user_id=user_id,
                            current_step=session.state.get("current_step", "S1"),
                            answers=session.state.get("answers", {}),
                            step_history=session.state.get("step_history", []),
                            is_audio_mode=is_audio
                        )
                        last_save_time = current_time
                        logger.debug(f"Periodic session save completed for user {user_id}")
                    except Exception as e:
                        logger.warning(f"Periodic session save failed for user {user_id}: {e}")
            
            # If loop finishes naturally, break outer loop
            print("[AGENT TO CLIENT] Stream finished naturally")
            break

        except WebSocketDisconnect:
            print("[AGENT TO CLIENT] WebSocket disconnected (normal)")
            break
        except asyncio.CancelledError:
            print("[AGENT TO CLIENT] Task cancelled")
            raise
        except Exception as e:
            # Handle Gemini/ADK connection errors with retry
            print(f"[AGENT TO CLIENT ERROR]: {e}")
            print(f"[AGENT TO CLIENT] Attempting to reconnect agent session...")
            
            # Retry reconnection with exponential backoff
            max_reconnect_retries = 5
            reconnect_delay = 0.5
            
            for reconnect_attempt in range(max_reconnect_retries):
                try:
                    await asyncio.sleep(reconnect_delay)
                    # Re-establish the agent connection
                    live_events = runner.run_live(
                        session=session,
                        live_request_queue=live_request_queue,
                        run_config=run_config,
                    )
                    print(f"[AGENT TO CLIENT] Agent session reconnected successfully (attempt {reconnect_attempt + 1})")
                    break  # Success, exit retry loop
                except Exception as reconnect_e:
                    if reconnect_attempt < max_reconnect_retries - 1:
                        reconnect_delay = min(reconnect_delay * 2, 10.0)  # Exponential backoff, max 10s
                        print(f"[AGENT TO CLIENT] Reconnection attempt {reconnect_attempt + 1} failed: {reconnect_e}, retrying in {reconnect_delay}s...")
                    else:
                        print(f"[AGENT TO CLIENT] Reconnection failed after {max_reconnect_retries} attempts: {reconnect_e}")
                        # Wait a bit longer before next retry loop
                        await asyncio.sleep(2.0)


async def client_to_agent_messaging(websocket, live_request_queue, session=None, user_id=None):
    """Client to agent communication. If session is provided (form mode), handles sync_state for manual Back."""
    try:
        while True:
            message_json = await websocket.receive_text()
            message = json.loads(message_json)

            # Form mode: handle manual back / sync_state (without changing core agent logic)
            if session is not None and isinstance(message, dict) and message.get("type") == "sync_state":
                # Complete state sync - update ALL state including full answers and history
                new_step = message.get("step", session.state.get("current_step", "S1"))
                new_answers = message.get("answers", {})  # Full answers dictionary
                new_history = message.get("step_history", [])  # Complete history
                
                # Update session state with complete information
                session.state["current_step"] = new_step
                session.state["answers"] = new_answers  # Replace with full answers
                session.state["step_history"] = new_history  # Replace with complete history
                
                print(f"[CLIENT TO AGENT] sync_state: step={new_step}, answers_count={len(new_answers)}, history_length={len(new_history)}")
                
                # Persist session state to database with retry logic
                if user_id:
                    await save_session_state_async(
                        user_id=user_id,
                        current_step=new_step,
                        answers=new_answers,
                        step_history=new_history,
                        is_audio_mode=session.state.get("is_audio_mode", False)
                    )
                
                # Immediately prompt agent to check current state and sync with screen
                # This ensures agent is always aware of current question on screen
                try:
                    prompt_message = Content(
                        role="user", 
                        parts=[Part.from_text(text="The user has changed the form state. Please immediately call get_current_question to see what question is currently on screen, then call get_survey_progress to understand the full context. Stay in sync with the screen.")]
                    )
                    live_request_queue.send_content(content=prompt_message)
                except Exception as e:
                    print(f"[CLIENT TO AGENT] Error sending sync prompt: {e}")
                    # Don't fail the sync_state operation if prompt fails
                continue

            mime_type = message.get("mime_type")
            data = message.get("data")
            if mime_type is None or data is None:
                raise ValueError("Message must have mime_type and data")

            if mime_type == "text/plain":
                # Retry sending text content
                max_send_retries = 3
                for send_attempt in range(max_send_retries):
                    try:
                        content = Content(role="user", parts=[Part.from_text(text=data)])
                        live_request_queue.send_content(content=content)
                        print(f"[CLIENT TO AGENT]: {data}")
                        break  # Success
                    except Exception as e:
                        if send_attempt < max_send_retries - 1:
                            await asyncio.sleep(0.2 * (send_attempt + 1))  # Small delay between retries
                            print(f"[CLIENT TO AGENT] Retry {send_attempt + 1}/{max_send_retries} sending text: {e}")
                        else:
                            print(f"[CLIENT TO AGENT] Error sending text content after {max_send_retries} attempts: {e}")
                            # Continue processing, don't crash
            elif mime_type == "audio/pcm":
                # Retry sending audio
                max_send_retries = 3
                for send_attempt in range(max_send_retries):
                    try:
                        decoded_data = base64.b64decode(data)
                        live_request_queue.send_realtime(Blob(data=decoded_data, mime_type=mime_type))
                        break  # Success
                    except Exception as e:
                        if send_attempt < max_send_retries - 1:
                            await asyncio.sleep(0.2 * (send_attempt + 1))  # Small delay between retries
                            print(f"[CLIENT TO AGENT] Retry {send_attempt + 1}/{max_send_retries} sending audio: {e}")
                        else:
                            print(f"[CLIENT TO AGENT] Error sending audio after {max_send_retries} attempts: {e}")
                            # Continue processing, don't crash
            else:
                print(f"[CLIENT TO AGENT] Unsupported mime type: {mime_type}")
                # Don't raise, just log and continue
    except WebSocketDisconnect:
        print("[CLIENT TO AGENT] WebSocket disconnected (normal)")
    except Exception as e:
        print(f"[CLIENT TO AGENT ERROR]: {e}")
        import traceback
        traceback.print_exc()
        raise


#
# FastAPI web app
#

app = FastAPI()

STATIC_DIR = Path("static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root():
    """Serves the form interface as root"""
    return FileResponse(os.path.join(STATIC_DIR, "form.html"))


# Form-related endpoints
@app.get("/form")
async def form_page():
    """Serves the form interface"""
    return FileResponse(os.path.join(STATIC_DIR, "form.html"))


@app.get("/api/survey-data")
async def get_survey_data():
    """Returns the filtered survey data structure (S1-S16 only for current version)"""
    return get_filtered_survey_data()


@app.get("/api/session/{user_id}")
async def get_session(user_id: str):
    """Get saved session data for a user"""
    try:
        session = db.load_session(user_id)
        if session:
            return {
                "success": True,
                "session": {
                    "current_step": session["current_step"],
                    "answers": session["answers"],
                    "step_history": session["step_history"],
                    "is_audio_mode": session.get("is_audio_mode", False)
                }
            }
        else:
            return {
                "success": False,
                "message": "No session found"
            }
    except Exception as e:
        logger.error(f"Error loading session for user {user_id}: {e}")
        return {
            "success": False,
            "message": f"Error loading session: {str(e)}"
        }


class NextStepRequest(BaseModel):
    current_step: str
    answer: Any
    answers: Dict[str, Any]


@app.post("/api/submit-answer")
async def submit_answer(req: NextStepRequest):
    """Validates answer and calculates the next step"""
    # Validate first
    is_valid, message = validate_answer(req.current_step, req.answer, req.answers)
    if not is_valid:
        return {"valid": False, "message": message}
    
    # Calculate next step
    next_step = get_next_step(req.current_step, req.answer, req.answers)
    return {"valid": True, "next_step": next_step}




async def save_session_state_async(user_id: str, current_step: str, answers: Dict[str, Any], 
                                   step_history: list, is_audio_mode: bool = False):
    """Save session state to database with retry logic"""
    async def _save():
        success = db.save_session(
            user_id=user_id,
            current_step=current_step,
            answers=answers,
            step_history=step_history,
            is_audio_mode=is_audio_mode
        )
        if not success:
            raise Exception(f"Database save returned False for user {user_id}")
        logger.debug(f"Session state saved for user {user_id}")
    
    try:
        await retry_func(
            _save,
            max_retries=3,
            initial_delay=0.5,
            exceptions=(Exception,)
        )
    except Exception as e:
        logger.error(f"Error saving session state for user {user_id} after retries: {e}")
        # Don't raise - allow session to continue even if save fails


async def start_form_agent_session(user_id, is_audio=False, initial_state=None):
    """Starts a form assistant agent session with session persistence"""
    
    # Try to load existing session from database
    if initial_state is None:
        try:
            saved_session = db.load_session(user_id)
            if saved_session:
                initial_state = {
                    "current_step": saved_session["current_step"],
                    "answers": saved_session["answers"],
                    "step_history": saved_session["step_history"]
                }
                logger.info(f"Resumed session for user {user_id} at step {initial_state['current_step']}")
            else:
                initial_state = {
                    "current_step": "S1",
                    "answers": {},
                    "step_history": []
                }
                logger.info(f"Starting new session for user {user_id}")
        except Exception as e:
            logger.error(f"Error loading session for user {user_id}: {e}")
            # Fallback to default initial state
            initial_state = {
                "current_step": "S1",
                "answers": {},
                "step_history": []
            }
    
    # Ensure step_history exists
    if "step_history" not in initial_state:
        initial_state["step_history"] = []
    
    # Create a Runner for form assistant
    runner = InMemoryRunner(
        app_name="Medical Survey Form",
        agent=form_assistant_agent,
    )
    
    # Create a Session with initial state
    session = await runner.session_service.create_session(
        app_name="Medical Survey Form",
        user_id=user_id,
        state=initial_state
    )
    
    # Set response modalities
    if is_audio:
        modalities = ["AUDIO"]
    else:
        modalities = ["TEXT"]
    
    # Configure RunConfig
    run_config = RunConfig(
        response_modalities=modalities,
        output_audio_transcription=types.AudioTranscriptionConfig() if is_audio else None,
        input_audio_transcription=types.AudioTranscriptionConfig() if is_audio else None,
    )
    
    # Create LiveRequestQueue
    live_request_queue = LiveRequestQueue()
    
    # Start agent session
    live_events = runner.run_live(
        session=session,
        live_request_queue=live_request_queue,
        run_config=run_config,
    )
    
    # Save initial session state to database
    try:
        db.save_session(
            user_id=user_id,
            current_step=initial_state["current_step"],
            answers=initial_state.get("answers", {}),
            step_history=initial_state.get("step_history", []),
            is_audio_mode=is_audio
        )
        logger.info(f"Initial session state saved for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to save initial session state for user {user_id}: {e}")
        # Continue even if save fails - session will still work
    
    return live_events, live_request_queue, session, runner


@app.websocket("/ws/form/{user_id}")
async def form_websocket_endpoint(websocket: WebSocket, user_id: str, is_audio: str = "false"):
    """WebSocket endpoint for form assistant"""
    
    # Wait for client connection
    await websocket.accept()
    print(f"[FORM] Client #{user_id} connected, awaiting handshake...")
    
    # Wait for initial state handshake
    try:
        handshake_json = await websocket.receive_text()
        handshake_data = json.loads(handshake_json)
        print(f"[FORM] Handshake received: {handshake_data}")
        
        initial_state = {
            "current_step": handshake_data.get("step", "S1"),
            "answers": handshake_data.get("answers", {}),
            "step_history": handshake_data.get("step_history", [])
        }
    except Exception as e:
        print(f"[FORM] Handshake failed or invalid, defaulting to S1. Error: {e}")
        initial_state = {"current_step": "S1", "answers": {}}
    
    print(f"[FORM] Starting session with step: {initial_state['current_step']}")
    
    # Start form agent session
    is_audio_mode = (is_audio == "true")
    live_events, live_request_queue, session, runner = await start_form_agent_session(user_id, is_audio_mode, initial_state)
    
    # Start tasks
    agent_to_client_task = asyncio.create_task(
        agent_to_client_messaging(websocket, live_events, session, is_audio_mode, runner, live_request_queue, user_id)
    )
    client_to_agent_task = asyncio.create_task(
        client_to_agent_messaging(websocket, live_request_queue, session=session, user_id=user_id)
    )
    
    # Wait until the websocket is disconnected or an error occurs
    try:
        tasks = [agent_to_client_task, client_to_agent_task]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Check if any task had an exception
        for task in done:
            try:
                task.result()
            except WebSocketDisconnect:
                pass
            except Exception as e:
                print(f"[FORM WEBSOCKET ERROR] Task failed: {e}")
                import traceback
                traceback.print_exc()
    finally:
        # Save final session state before disconnecting
        try:
            final_state = {
                "current_step": session.state.get("current_step", "S1"),
                "answers": session.state.get("answers", {}),
                "step_history": session.state.get("step_history", [])
            }
            db.save_session(
                user_id=user_id,
                current_step=final_state["current_step"],
                answers=final_state["answers"],
                step_history=final_state["step_history"],
                is_audio_mode=is_audio_mode
            )
            logger.info(f"Final session state saved for user {user_id} before disconnect")
        except Exception as e:
            logger.error(f"Failed to save final session state for user {user_id}: {e}")
        
        # Close LiveRequestQueue
        live_request_queue.close()
        
        # Disconnected
        print(f"[FORM] Client #{user_id} disconnected")

