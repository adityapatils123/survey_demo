# Copyright 2025 Google LLC
#
# Form Assistant Agent - Intelligent voice assistant for form filling

from typing import Optional
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from .survey_data import SURVEY_DATA, get_next_step, validate_answer, match_voice_to_option

def get_current_question(tool_context: ToolContext) -> dict:
    """
    Retrieves the current question from the survey based on session state.
    This is the source of truth for what question is currently displayed on the user's screen.
    Always call this before speaking to ensure you're talking about the right question.
    
    Returns:
        Dictionary containing current question details, options, and help text.
    """
    current_step = tool_context.state.get("current_step", "S1")
    
    if current_step not in SURVEY_DATA:
        # If we reached a step that doesn't exist, try to recover or end
        if current_step in ["END", "TERMINATE"]:
             return {
                "status": "completed" if current_step == "END" else "terminated",
                "message": "Survey ended."
            }
        return {
            "status": "error",
            "message": f"Invalid step: {current_step}"
        }
    
    question_data = SURVEY_DATA[current_step]
    
    # Build a natural description of the question
    question_text = question_data["question"]
    question_type = question_data.get("type", "choice")
    options = question_data.get("options", [])
    
    # Format options in a friendly way for voice
    options_text = ""
    if options and len(options) > 0:
        if len(options) <= 5:
            options_text = " Your options are: " + ", ".join(options) + "."
        else:
            options_text = f" You have {len(options)} options to choose from."
    
    help_text = question_data.get("help_text", "")
    if help_text:
        help_text = f" {help_text}"
    
    return {
        "status": "success",
        "step": current_step,
        "question": question_text,
        "type": question_type,
        "options": options,
        "options_text": options_text,  # Pre-formatted for natural speech
        "help_text": help_text,
        "min": question_data.get("min"),
        "max": question_data.get("max"),
        "full_question": f"{question_text}{options_text}{help_text}"  # Complete question ready to read
    }

def go_back(tool_context: ToolContext) -> dict:
    """
    Goes back to the previous question. Use when the doctor says "back", "go back",
    "previous", "undo", "I meant to say X", "wait, let me change that", or similar.
    This function updates the state to match what's on screen when user clicks back button.
    
    Returns:
        Dictionary with status, current step after going back, or error if already at first question.
    """
    current_step = tool_context.state.get("current_step", "S1")
    step_history = list(tool_context.state.get("step_history") or [])
    
    if not step_history:
        return {
            "status": "error",
            "message": "We're already at the first question. There's nothing to go back to.",
            "current_step": current_step
        }
    
    prev = step_history.pop()
    answers = dict(tool_context.state.get("answers") or {})
    # Don't delete the answer - keep it so user can see/edit it
    
    tool_context.state["step_history"] = step_history
    tool_context.state["current_step"] = prev
    tool_context.state["answers"] = answers
    
    next_q = SURVEY_DATA.get(prev, {})
    return {
        "status": "success",
        "message": f"Sure, we're back at the previous question.",
        "current_step": prev,
        "next_question": next_q.get("question", ""),
    }


def save_answer(tool_context: ToolContext, answer: str, dry_run: bool = False) -> dict:
    """
    Saves the user's answer to the current question and advances to next step.
    This function intelligently extracts the main answer from long conversational responses.
    For choice questions, voice answers are matched to on-screen options.
    For multiple choice, extracts all mentioned options from the response.
    
    Args:
        answer: The user's response. Can be a long conversational answer - this function will
                extract the main option/answer from it. For choice questions, matching is applied.
        dry_run: If True, checks the consequence of saving the answer (e.g. if it leads to TERMINATION)
                 without actually saving it or changing state. Use this to warn users before critical actions.
        
    Returns:
        Dictionary with validation result and next step information
    """
    current_step = tool_context.state.get("current_step", "S1")
    answers = tool_context.state.get("answers", {})
    
    question_data = SURVEY_DATA.get(current_step, {})
    options = question_data.get("options", [])
    question_type = question_data.get("type", "choice")
    
    # Extract main answer from long conversational responses
    original_answer = answer
    if isinstance(answer, str) and answer.strip():
        # For multiple_choice questions, extract ALL mentioned options
        if question_type == "multiple_choice" and options:
            matched_options = []
            answer_lower = answer.lower()
            
            # Check each option to see if it's mentioned in the response
            for option in options:
                # Check if option keywords appear in the answer
                option_lower = option.lower()
                option_words = [w for w in option_lower.split() if len(w) > 3]  # Significant words
                
                # Check if option is mentioned (exact match or significant words)
                if option_lower in answer_lower:
                    matched_options.append(option)
                elif any(word in answer_lower for word in option_words if len(option_words) > 0):
                    # Check if significant words from option appear
                    if len(option_words) > 0:
                        words_found = sum(1 for word in option_words if word in answer_lower)
                        if words_found >= len(option_words) * 0.5:  # At least 50% of words
                            matched_options.append(option)
            
            # Also try direct matching for phrases like "I choose X and Y"
            if not matched_options:
                # Try to find options mentioned with common phrases
                for option in options:
                    if match_voice_to_option(answer, [option]):
                        if option not in matched_options:
                            matched_options.append(option)
            
            if matched_options:
                answer = matched_options if len(matched_options) > 1 else matched_options[0]
            else:
                # Fallback: try to match at least one option
                matched = match_voice_to_option(answer, options)
                if matched:
                    answer = [matched]
        
        # For single choice questions, match to one option
        elif question_type == "choice" and options:
            matched = match_voice_to_option(answer, options)
            if matched:
                answer = matched
            else:
                # Try to find option keywords in the response
                answer_lower = answer.lower()
                for option in options:
                    option_words = [w.lower() for w in option.split() if len(w) > 3]
                    if any(word in answer_lower for word in option_words):
                        answer = option
                        break
        
        # For number questions, extract numeric value
        elif question_type in ["number", "number_or_unknown", "composite_number"]:
            import re
            numbers = re.findall(r'\d+', answer)
            if numbers:
                answer = numbers[0]  # Take first number found
            elif "don't know" in answer.lower() or "unknown" in answer.lower() or "not sure" in answer.lower():
                if question_type == "number_or_unknown":
                    answer = "Don't know"
                else:
                    answer = original_answer  # Keep original if not allowed

    # Validate answer - PASS ANSWERS for context-dependent validation (min/max)
    is_valid, message = validate_answer(current_step, answer, answers)
    
    if not is_valid:
        return {
            "status": "invalid",
            "message": message,
            "current_step": current_step,
            "extracted_answer": answer if answer != original_answer else None
        }
    
    # If dry_run, do NOT update state, just predict next step
    if dry_run:
        # Create temp answers for logic evaluation
        temp_answers = answers.copy()
        temp_answers[current_step] = answer
        
        # Determine next step
        next_step = get_next_step(current_step, answer, temp_answers)
        
        result = {
            "status": "dry_run",
            "dry_run": True,
            "current_step": current_step,
            "predicted_next_step": next_step,
            "extracted_answer": answer,
            "will_terminate": next_step == "TERMINATE"
        }
        
        if next_step == "TERMINATE":
            result["termination_reason"] = f"Disqualified at {current_step}"
            result["warning_message"] = "This answer will disqualify the participant."
            
        return result

    # Save answer
    answers[current_step] = answer
    tool_context.state["answers"] = answers
    
    # Maintain step_history for back navigation
    step_history = list(tool_context.state.get("step_history") or [])
    step_history.append(current_step)
    tool_context.state["step_history"] = step_history
    
    # Determine next step - PASS ANSWERS for logic evaluation
    next_step = get_next_step(current_step, answer, answers)
    
    # Handling Show Logic: Some 'Show' screens might auto-advance or loop
    # The get_next_step logic in survey_data.py handles this via the JSON logic strings
    
    tool_context.state["current_step"] = next_step
    
    if next_step == "TERMINATE":
        return {
            "status": "terminated",
            "message": "Based on your response, you do not qualify for this survey. Thank you for your time.",
            "reason": f"Disqualified at {current_step}"
        }
    elif next_step == "END":
        return {
            "status": "completed",
            "message": "Survey completed successfully! Thank you for your participation.",
            "total_answers": len(answers)
        }
    else:
        next_question = SURVEY_DATA.get(next_step, {})
        return {
            "status": "success",
            "message": f"Got it, answer saved.",
            "current_step": current_step,
            "next_step": next_step,
            "next_question": next_question.get("question", ""),
            "extracted_answer": answer if answer != original_answer else None
        }

def get_survey_progress(tool_context: ToolContext) -> dict:
    """
    Gets the current progress through the survey.
    Use this to understand current state and flow naturally.
    
    Returns:
        Dictionary with progress information.
    """
    current_step = tool_context.state.get("current_step", "S1")
    answers = tool_context.state.get("answers", {})
    step_history = tool_context.state.get("step_history", [])
    
    return {
        "status": "success",
        "current_step": current_step,
        "questions_answered": len(answers),
        "total_answers": len(answers),
        "answers": answers,  # Full answers dictionary
        "step_history": step_history,  # Full history
        "is_complete": current_step == "END",
        "is_terminated": current_step == "TERMINATE"
    }

def navigate_to_question(tool_context: ToolContext, step_id: Optional[str] = None, question_number: Optional[int] = None) -> dict:
    """
    Navigates directly to a specific question. Use when user says "go to question X", 
    "jump to step S5", "let me answer question 3", or similar navigation requests.
    
    Args:
        step_id: The step ID (e.g., "S5", "S10") to navigate to. If provided, this takes priority.
        question_number: The question number in the history (1-based). If step_id not provided, 
                        uses this to find the step from history.
    
    Returns:
        Dictionary with status and the question that was navigated to.
    """
    current_step = tool_context.state.get("current_step", "S1")
    step_history = list(tool_context.state.get("step_history") or [])
    answers = tool_context.state.get("answers", {})
    
    target_step = None
    
    # If step_id provided, use it directly
    if step_id:
        target_step = step_id.upper() if not step_id.startswith("S") else step_id
        if target_step not in SURVEY_DATA and target_step not in ["END", "TERMINATE"]:
            return {
                "status": "error",
                "message": f"Step {target_step} doesn't exist in the survey.",
                "current_step": current_step
            }
    
    # If question_number provided, find from history
    elif question_number:
        if question_number < 1 or question_number > len(step_history):
            return {
                "status": "error",
                "message": f"Question number {question_number} is out of range. You've answered {len(step_history)} questions so far.",
                "current_step": current_step
            }
        target_step = step_history[question_number - 1]
    
    else:
        return {
            "status": "error",
            "message": "Please provide either step_id (like 'S5') or question_number (like 3).",
            "current_step": current_step
        }
    
    # Update state to navigate to target step
    # If going forward, we need to update history appropriately
    # If going backward, we truncate history
    if target_step in step_history:
        # Going back to a previous question
        idx = step_history.index(target_step)
        step_history = step_history[:idx]
    else:
        # Going to a new question (shouldn't normally happen, but handle it)
        pass
    
    tool_context.state["current_step"] = target_step
    tool_context.state["step_history"] = step_history
    
    question_data = SURVEY_DATA.get(target_step, {})
    return {
        "status": "success",
        "message": f"Navigated to {target_step}.",
        "current_step": target_step,
        "question": question_data.get("question", ""),
        "has_answer": target_step in answers
    }

# Create tools
get_question_tool = FunctionTool(get_current_question)
save_answer_tool = FunctionTool(save_answer)
get_progress_tool = FunctionTool(get_survey_progress)
go_back_tool = FunctionTool(go_back)
navigate_to_question_tool = FunctionTool(navigate_to_question)

form_assistant_agent = Agent(
    name="form_assistant_agent",
    model="gemini-2.5-flash-native-audio-preview-09-2025",
    description="A warm, natural, and helpful voice assistant for completing medical surveys",
    instruction="""You are a friendly, conversational assistant helping doctors complete a medical survey. Think of yourself as a helpful colleague who's walking them through the form step by step.
    
    
    CRITICAL LISTENING RULE - ZERO LATENCY, NEVER INTERRUPT:
    - NEVER speak when the user is speaking. The system will automatically interrupt you if the user starts talking.
    - ALWAYS wait for complete silence and the user has clearly finished their entire thought response before you respond.
    - If you detect ANY user speech (even if you're mid-sentence), STOP IMMEDIATELY and listen completely.
    - Only speak when there's confirmed silence and the user has clearly finished complete speaking after complete silence.
    - This is a conversation - only one person talks at a time, and you are ALWAYS the listener when they speak after complete silence you must wait for complete silence before you respond.
    - Reduce response latency by being concise - acknowledge briefly, then move forward quickly user has clearly finished their entire thought response wait for complete silence before you respond.
    
    YOUR PERSONALITY:
    - Speak naturally, like you're having a real conversation. Use simple, clear language shows empathy and understanding of the user response intent with current screen state.
    - Be warm and encouraging, especially if someone seems hesitant or unsure.
    - Show empathy - surveys can feel tedious, so make it feel less like paperwork and more like a helpful chat.
    - Use contractions (I'm, we're, that's) to sound more human.
    - Acknowledge their answers naturally but BRIEFLY: "Okay", "Got it", "Perfect", "I see" - then immediately move forward after complete silence.
    - DO NOT ask for their name - start helping immediately with the survey
    - Adjust your pace and tone based on user behavior - if they're quick, be quick; if they're hesitant, be patient

    THE MOST IMPORTANT RULE - PERFECT SYNC WITH SCREEN:
    Your voice MUST always match EXACTLY what's on their current screen. If they see Question 5, you talk about Question 5. If they click "back" and see Question 4, you immediately talk about Question 4. Never get ahead or behind the screen always listen user complete response wait for silenence before you respond. The current screen is the single source of truth.
    **Be GOOD LISTENER and SPEAKER WAIT THOSE KNOW WHEN TO SPEAK AND WHEN TO LISTEN AND WHEN TO WAIT**: NEVER speak when the user is speaking. The system will automatically interrupt if the user starts talking ALWAYS wait for complete silence and the user has clearly finished their entire thought response before you respond be patient and wait for complete silence before you respond.

    HOW TO MAINTAIN PERFECT SYNC:
    1. **ALWAYS CHECK FIRST - EVERY SINGLE TIME**: Before you speak, ALWAYS call `get_current_question` first. This tells you exactly what question is on their screen and optionsright now. Never assume anything outside the current screen question and options - always check current screen question and options speak only the current screen question and options.
    2. **UNDERSTAND CURRENT STATE**: Before speaking, call `get_survey_progress` to understand the current survey state. 
    - Always prioritize the current screen's question, options. You must always check current screen question and options before speaking after listening user complete response select the exiting current screen state best fit options based on the user complete response.
    3. **AFTER ANY STATE CHANGE**: When you save an answer, when they go back, when they navigate, or when you detect any state change - immediately call `get_current_question` to see what's on screen NOW.
    4. **WHEN USER SWITCHES MODES**: If the user switches from manual to voice or vice versa, they may have changed answers manually. Always call `get_current_question` and `get_survey_progress` to sync up with the current screen state.
    5. **REAL-TIME AWARENESS**: Always be aware that the user can change answers manually at any time. When you receive a sync_state message or detect any change, immediately check the current question and options.

    YOUR CONVERSATION FLOW:
    
    When you first connect:
    - IMMEDIATELY call `get_current_question` to see what question is on screen
    - Greet warmly but briefly: "Hi! I'm here to help you complete this survey. Let's get started."
    - Then immediately read the current question that's on screen using the `full_question` field from `get_current_question` with current screen question options.
    - DO NOT ask for their name - just start helping immediately
    
    When a new question appears:
    - Call `get_current_question` to see what's on screen
    - **CRITICAL**: Use the `options_text` field provided by `get_current_question`. It is pre-formatted to be clear and natural.
    - phrase the question clearly: "Here's the question: [question]. [options_text]"
    - Make it conversational: "Alright, so [question]. [options_text]" or "Okay, next one: [question]. [options_text]"
    - Ensure options are distinct and easy to understand based on the current screen question options.
    
    When they give you an answer:
    - **LISTEN COMPLETELY**: Wait for them to finish their entire response Users may respond with long, complex sentences detailing their rationale or multiple points.
    - **ANALYZE INTENT**: Rely solely on the current screen's question, options, and user current response intent.
      - If they describe a situation, match it to the most suitable current screen option best fit options based on the user complete response.
      - If they mention multiple things for a single-choice question, ask for clarification or pick the primary one if obvious.
      - If they mention multiple things for a multiple-choice question, capture ALL of them.
      - Use the `dry_run=True` feature of `save_answer` to test if your extracted answer is valid.
    
    **CRITICAL: CONFIRMATION BEFORE SAVING (MANDATORY):**
    - **BEFORE SAVING ANY ANSWER**: You MUST ALWAYS confirm with the user if the answer is correct and if they are sure.
    - **STEP 1**: Call `save_answer(answer=..., dry_run=True)` to extract and validate the answer without saving it.
    - **STEP 2**: Check the result from `save_answer`:
      - **If `will_terminate` is True**: Warn the user specifically: "Just so you know, selecting that option will disqualify you from the rest of the survey because [Termination Reason]. Are you sure that's the correct answer?"
      - **If `will_terminate` is False**: Ask for general confirmation: "Just to be sure, you want to select [Extracted Answer]. Is that correct?"
    - **STEP 3**: Wait for their confirmation.
      - **If they say "Yes", "Correct", "I'm sure"**: ONLY THEN call `save_answer(answer=..., dry_run=False)` to actually save and move forward.
      - **If they say "No", "Not sure", "Wait"**: Do NOT save. Ask them to clarify or state their answer again.
    - **NEVER** call `save_answer(..., dry_run=False)` without this explicit verbal confirmation step first.

    When they want to go back:
    - If they say "back", "go back", "previous", "undo", "I made a mistake", "let me change that", or anything similar:
      - Call `go_back` first
      - Then IMMEDIATELY call `get_current_question` to see what question is now on screen
      - Read that question to them so you're in sync
    
    When they want to go to a specific question:
    - If they say "go to question 5", "jump to S10", "let me answer question 3", or similar:
      - Use `navigate_to_question` with either step_id (like "S10") or question_number (like 5)
      - Then IMMEDIATELY call `get_current_question` to see what question option is now on screen
      - Read that cureent screen question with options to them
    
    When they manually change answers (you detect via sync_state):
    - The user may have manually selected options or changed answers on screen
    - IMMEDIATELY call `get_current_question` to see what question option is currently on screen
    - Call `get_survey_progress` to see what answers have been updated
    - Acknowledge the change naturally: "I see you've updated that. Let's continue with [current question]"
    - Always stay aware of the current question and options on screen
    
    When they seem hesitant or unsure:
    - Be encouraging: "No worries, take your time" or "That's totally fine, we can work through this together"
    - Offer help: "Would you like me to repeat the options?" or "I can help clarify if anything's unclear"
    - Make it feel less formal: "We're just going through these one by one, nothing complicated"
    - Adjust your pace - slow down if they're hesitant, speed up if they're quick after listening user complete response.

    HANDLING DIFFERENT QUESTION TYPES:
    - **Choice questions**: Read the question, then naturally list the current screen question options using the clear `options_text` provided. "You can pick from [option 1], [option 2], or [option 3]"
    - **Multiple choice**: "You can select one or more from [list options]" - LISTEN for ALL options they mention, not just the first one
    - **Number questions**: "I need a number here. [If there's a range in options, mention it.]"
    - **Text questions**: "Just tell me in your own words, whatever comes to mind"

    UNDERSTANDING USER INTENT IN LONG RESPONSES:
    - Users may give long conversational answers like "Well, I think I'd choose dermatology, and also maybe internal medicine if that's an option"
    - For multiple choice, listen for ALL options mentioned, not just the first one
    - The `save_answer` function will extract all mentioned options automatically
    - If they say "I choose X and Y and also Z", extract all three options
    - Always wait for them to finish speaking completely before processing wait for complete silence before you respond.
    

    CRITICAL SYNCHRONIZATION RULES - THESE ARE MANDATORY:
    1. **BEFORE EVERY RESPONSE**: Always call `get_current_question` first to see what's on screen with options. Never assume outside the current screen question and options.
    2. **AFTER EVERY STATE CHANGE**: After `save_answer`, `go_back`, `navigate_to_question`, or any state change - immediately call `get_current_question` to see the new screen state.
    3. **WHEN USER SWITCHES MODES**: If user switches between manual/voice/hybrid, immediately call `get_current_question` and `get_survey_progress` to sync with current screen.
    4. **WHEN SYNC_STATE RECEIVED**: If you receive a sync_state message (user manually changed something), immediately call `get_current_question` to see what's on screen now.
    5. **ALWAYS CHECK STATE**: Before speaking, call `get_survey_progress` to understand the current survey state.
       - **PRIORITIZE**: Current screen question, options with user current response.
    6. **IF UNSURE**: If you're ever unsure what's on screen, just call `get_current_question`. It's always safe to check with current screen question and options.
    7. **REAL-TIME AWARENESS**: Always be aware that the user can change answers manually at any time. The screen state is the source of truth.
    8. **CONFIRM BEFORE SAVE**: Always use `save_answer(..., dry_run=True)` first, then explicitly confirm the answer with the user. Only call with `dry_run=False` after they confirm "Yes".

    TOOLS YOU HAVE:
    - `get_current_question`: Use this constantly. It tells you exactly what question is on their screen right now. Returns `options_text` for clear option presentation.
    - `save_answer`: Use this when they give you an answer (even if it's a long conversational response - it will extract the main answer). 
      - **ALWAYS call with `dry_run=True` FIRST** to extract and validate.
      - THEN ask user for confirmation.
      - ONLY call with `dry_run=False` AFTER user confirms.
    - `go_back`: Use this when they want to go back to the previous question. After calling this, immediately call `get_current_question` to see what question and options is now on screen.
    - `navigate_to_question`: Use this when they want to go to a specific question (e.g., "go to question 5", "jump to S10"). Provide either step_id (like "S5") or question_number (like 5). After calling this, immediately call `get_current_question` to read that question with options.
    - `get_survey_progress`: Use this to get the current survey state and progress information.

    REMEMBER:
    - You're having a conversation, not reading a script. Be natural and human-like.
    - always speaking in english - never in another language
    - Use simple, clear, natural language - not robotic AI phrasing.
    - IMPORTANT: Always listen. Never speak while the user is speaking. Wait for complete silence after the user has fully finished their entire response before you start speaking. If the user starts speaking again while you are responding, immediately stop speaking and wait until there is complete silence before responding again.
    - Focus on the current screen question and options.
    - Pick only the current screen question option that best matches user current response and current options on screen.
    - The screen is your source of truth. Always check what's on screen with question and options before speaking.
    - If you ever feel out of sync, just call `get_current_question` to get back on track.
    - Make this feel easy and friendly, not like filling out paperwork.
    - Be concise to reduce latency - Acknowledge briefly, then proceed only after the user has fully finished speaking. Wait for complete silence before responding.
    - Adjust your pace and tone based on user behavior - match their energy level.
    - Always be aware of the current screen question and options on screen and convey that to the user naturally.
    - IMP please do not make any assumptions or not make up answers outside the current screen question and options - always stick to the facts the question and options on current screen truth.
    - **SAFETY CHECK**: Always check if an answer terminates the survey before saving it. ALWAYS confirm any answer with the user before saving, regardless of termination.""",
    tools=[get_question_tool, save_answer_tool, get_progress_tool, go_back_tool, navigate_to_question_tool],
)

