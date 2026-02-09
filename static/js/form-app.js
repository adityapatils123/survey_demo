/**
 * Form Application - Medical Survey with Voice Assistant
 * Handles both manual and voice-based form filling
 */

// State management
const state = {
    currentStep: 'S1',
    answers: {},
    stepHistory: [],  // path of steps visited, for back navigation (branching-aware)
    mode: 'manual', // 'manual' or 'voice'
    websocket: null,
    isVoiceActive: false,
    audioPlayerNode: null,
    audioRecorderNode: null,
    sessionId: Math.random().toString().substring(10)
};

// DOM Elements
const elements = {
    questionNumber: document.getElementById('questionNumber'),
    questionText: document.getElementById('questionText'),
    helpText: document.getElementById('helpText'),
    formGroup: document.getElementById('formGroup'),
    nextBtn: document.getElementById('nextBtn'),
    backBtn: document.getElementById('backBtn'),
    statusMessage: document.getElementById('statusMessage'),
    formContent: document.getElementById('formContent'),
    completionScreen: document.getElementById('completionScreen'),
    manualModeBtn: document.getElementById('manualModeBtn'),
    voiceModeBtn: document.getElementById('voiceModeBtn'),
    startVoiceBtn: document.getElementById('startVoiceBtn'),
    stopVoiceBtn: document.getElementById('stopVoiceBtn'),
    voiceIndicator: document.getElementById('voiceIndicator'),
    assistantStatus: document.getElementById('assistantStatus'),
    progressBar: document.getElementById('progressBar'),
    progressText: document.getElementById('progressText'),
    answersList: document.getElementById('answersList'),
    downloadBtn: document.getElementById('downloadBtn'),
    toggleProgressBtn: document.getElementById('toggleProgressBtn'),
    surveyProgressContainer: document.getElementById('surveyProgressContainer'),
    progressQuestionsList: document.getElementById('progressQuestionsList')
};

// Survey data (loaded from server)
let surveyData = {};

// Initialize
async function init() {
    console.log('[INIT] Starting form application');

    // Load survey data
    await loadSurveyData();

    // Setup event listeners
    setupEventListeners();

    // Load first question
    loadQuestion(state.currentStep);

    // Update progress (including comprehensive panel)
    updateProgress();
    
    // Initialize progress panel (collapsed by default)
    if (elements.surveyProgressContainer) {
        updateSurveyProgressPanel();
    }
}

// Load survey data from server
async function loadSurveyData() {
    try {
        const response = await fetch('/api/survey-data');
        surveyData = await response.json();
        console.log('[SURVEY] Data loaded:', Object.keys(surveyData).length, 'questions');
    } catch (error) {
        console.error('[SURVEY] Error loading data:', error);
        showStatus('Error loading survey data. Please refresh.', 'error');
    }
}

// Setup event listeners
function setupEventListeners() {
    // Mode toggle
    elements.manualModeBtn.addEventListener('click', () => switchMode('manual'));
    elements.voiceModeBtn.addEventListener('click', () => switchMode('voice'));

    // Navigation buttons
    elements.nextBtn.addEventListener('click', handleNext);
    elements.backBtn.addEventListener('click', handleBack);

    // Voice controls
    elements.startVoiceBtn.addEventListener('click', startVoiceMode);
    elements.stopVoiceBtn.addEventListener('click', stopVoiceMode);

    // Download button
    elements.downloadBtn.addEventListener('click', downloadResults);

    // Toggle progress panel
    if (elements.toggleProgressBtn) {
        elements.toggleProgressBtn.addEventListener('click', toggleProgressPanel);
    }
}

// Switch between manual and voice mode
function switchMode(mode) {
    state.mode = mode;

    if (mode === 'manual') {
        elements.manualModeBtn.classList.add('active');
        elements.voiceModeBtn.classList.remove('active');
        elements.assistantStatus.textContent = 'Standby';
        if (state.isVoiceActive) {
            stopVoiceMode();
        }
    } else {
        elements.manualModeBtn.classList.remove('active');
        elements.voiceModeBtn.classList.add('active');
        elements.assistantStatus.textContent = 'Ready to assist';
        
        // If voice is active, sync state immediately when switching to voice mode
        if (state.isVoiceActive && state.websocket && state.websocket.readyState === WebSocket.OPEN) {
            syncStateToAgent();
            // Prompt agent to check current state
            setTimeout(() => {
                if (state.websocket && state.websocket.readyState === WebSocket.OPEN) {
                    state.websocket.send(JSON.stringify({
                        mime_type: 'text/plain',
                        data: 'I just switched to voice mode. Please check the current state and read the question that\'s on screen.'
                    }));
                }
            }, 100);
        }
    }

    console.log('[MODE] Switched to:', mode);
}

// Load a question
function loadQuestion(step) {
    const question = surveyData[step];
    if (!question) {
        console.error('[QUESTION] Invalid step:', step);
        return;
    }

    console.log('[QUESTION] Loading:', step, question.question);

    // Update question display (branching-aware: use stepHistory length + 1)
    const questionNum = state.stepHistory.length + 1;
    elements.questionNumber.textContent = `Question ${questionNum}`;
    
    // Evaluate piped variables in question text (e.g., {Output['S1']})
    // Simple client-side replacement if needed, but python usually handles this better.
    // Ideally, the server should return the pre-processed text, but we only have raw data here.
    // For now, let's just show raw text or minimal replacement.
    // NOTE: The python agent does "get_piped_question". We might want an API for this if critical.
    // For now, we will display raw text. User logic handles complex text.
    elements.questionText.textContent = question.question;
    elements.helpText.textContent = question.help_text || '';

    // Clear previous form controls
    elements.formGroup.innerHTML = '';

    // Create appropriate form control
    if (question.type === 'choice') {
        createRadioGroup(question.options, step);
    } else if (question.type === 'multiple_choice') {
        createCheckboxGroup(question.options, step);
    } else if (question.type === 'number') {
        createNumberInput(question, step);
    } else if (question.type === 'number_or_unknown') {
        createNumberOrUnknownInput(question, step);
    } else if (question.type === 'text') {
        createTextArea(step);
    } else if (question.type === 'composite_number') {
        createCompositeInput(question, step);
    } else if (question.type === 'show') {
        createShowScreen();
    } else {
        // Fallback for unknown types
        createTextArea(step);
    }

    // Update back button (branching-aware: no back when stepHistory is empty)
    elements.backBtn.disabled = state.stepHistory.length === 0;

    // If in voice mode and active, ask the question
    if (state.mode === 'voice' && state.isVoiceActive) {
        askQuestionVoice(question);
    }
}

// Create radio button group
function createRadioGroup(options, step) {
    const radioGroup = document.createElement('div');
    radioGroup.className = 'radio-group';

    options.forEach((option, index) => {
        const optionDiv = document.createElement('div');
        optionDiv.className = 'radio-option';

        const radio = document.createElement('input');
        radio.type = 'radio';
        radio.name = `question_${step}`;
        radio.value = option;
        radio.id = `option_${step}_${index}`;

        // Pre-select if already answered
        if (state.answers[step] === option) {
            radio.checked = true;
            optionDiv.classList.add('selected');
        }

        const label = document.createElement('label');
        label.htmlFor = radio.id;
        label.textContent = option;

        // Handle selection
        radio.addEventListener('change', () => {
            document.querySelectorAll('.radio-option').forEach(opt => {
                opt.classList.remove('selected');
            });
            optionDiv.classList.add('selected');
            state.answers[step] = option;
            
            // Sync state to voice agent if active (user manually changed answer)
            syncStateToAgent();
            updateProgress(); // Update progress panel instantly
        });

        optionDiv.appendChild(radio);
        optionDiv.appendChild(label);
        radioGroup.appendChild(optionDiv);
    });

    elements.formGroup.appendChild(radioGroup);
}

// Create checkbox group (Multiple Choice)
function createCheckboxGroup(options, step) {
    const group = document.createElement('div');
    group.className = 'radio-group'; // Reuse styling

    // Ensure answer is array
    let currentAnswers = state.answers[step];
    if (typeof currentAnswers === 'string') {
        // Try to parse if it looks like a list string or just wrap it
        currentAnswers = [currentAnswers]; 
    } else if (!Array.isArray(currentAnswers)) {
        currentAnswers = [];
    }

    options.forEach((option, index) => {
        const optionDiv = document.createElement('div');
        optionDiv.className = 'radio-option'; // Reuse styling

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.name = `question_${step}`;
        checkbox.value = option;
        checkbox.id = `chk_${step}_${index}`;

        if (currentAnswers.includes(option)) {
            checkbox.checked = true;
            optionDiv.classList.add('selected');
        }

        const label = document.createElement('label');
        label.htmlFor = checkbox.id;
        label.textContent = option;

        checkbox.addEventListener('change', () => {
            optionDiv.classList.toggle('selected', checkbox.checked);
            
            // Update state
            const selected = [];
            group.querySelectorAll('input:checked').forEach(cb => selected.push(cb.value));
            // Store as string list for compatibility or just list
            // Python logic handles lists or strings. Let's store as list.
            state.answers[step] = selected;
            
            // Sync state to voice agent if active (user manually changed answer)
            syncStateToAgent();
            updateProgress(); // Update progress panel instantly
        });

        optionDiv.appendChild(checkbox);
        optionDiv.appendChild(label);
        group.appendChild(optionDiv);
    });

    elements.formGroup.appendChild(group);
}

// Create number input
function createNumberInput(question, step) {
    const input = document.createElement('input');
    input.type = 'number';
    input.className = 'number-input';
    input.placeholder = `Enter a number${question.min !== undefined ? ` (${question.min}-${question.max})` : ''}`;
    if (question.min !== undefined) input.min = question.min;
    if (question.max !== undefined && typeof question.max === 'number') input.max = question.max;

    // Pre-fill if already answered
    if (state.answers[step]) {
        input.value = state.answers[step];
    }

    // Save on change
    input.addEventListener('input', () => {
        state.answers[step] = input.value;
        syncStateToAgent();
    });

    elements.formGroup.appendChild(input);
}

// Create number or unknown input
function createNumberOrUnknownInput(question, step) {
    // Container
    const container = document.createElement('div');
    
    // Number input
    const input = document.createElement('input');
    input.type = 'number';
    input.className = 'number-input';
    input.placeholder = "Enter value";
    input.style.marginBottom = '12px';
    
    if (state.answers[step] && !isNaN(state.answers[step])) {
        input.value = state.answers[step];
    }

    // Options (e.g. "Don't know")
    const optionsGroup = document.createElement('div');
    optionsGroup.className = 'radio-group';
    
    if (question.options) {
        question.options.forEach((opt, idx) => {
            const optDiv = document.createElement('div');
            optDiv.className = 'radio-option';
            
            const radio = document.createElement('input');
            radio.type = 'radio'; // Use radio to mutually exclude with number? Or checkbox?
            // Usually "Don't know" clears the number.
            radio.name = `dk_${step}`;
            radio.id = `dk_${step}_${idx}`;
            radio.value = opt;
            
            if (state.answers[step] === opt) {
                radio.checked = true;
                optDiv.classList.add('selected');
                input.disabled = true;
            }

            const label = document.createElement('label');
            label.htmlFor = radio.id;
            label.textContent = opt;
            
            radio.addEventListener('change', () => {
                if (radio.checked) {
                    input.value = '';
                    input.disabled = true;
                    state.answers[step] = opt;
                    optDiv.classList.add('selected');
                    syncStateToAgent();
                }
            });
            
            optDiv.appendChild(radio);
            optDiv.appendChild(label);
            optionsGroup.appendChild(optDiv);
        });
    }

    // Reactivate number input when typing
    input.addEventListener('input', () => {
        // Uncheck options
        optionsGroup.querySelectorAll('input').forEach(r => {
            r.checked = false;
            r.closest('.radio-option').classList.remove('selected');
        });
        state.answers[step] = input.value;
        syncStateToAgent();
    });
    
    // Enable input if clicking it
    input.addEventListener('focus', () => {
        input.disabled = false;
    });

    container.appendChild(input);
    container.appendChild(optionsGroup);
    elements.formGroup.appendChild(container);
}

// Create text area
function createTextArea(step) {
    const textarea = document.createElement('textarea');
    textarea.className = 'number-input'; // Reuse style
    textarea.style.minHeight = '100px';
    textarea.style.fontFamily = 'inherit';
    textarea.placeholder = "Type your answer here...";
    
    if (state.answers[step]) {
        textarea.value = state.answers[step];
    }
    
    textarea.addEventListener('input', () => {
        state.answers[step] = textarea.value;
        syncStateToAgent();
    });
    
    elements.formGroup.appendChild(textarea);
}

// Create composite input (multiple fields)
function createCompositeInput(question, step) {
    const container = document.createElement('div');
    container.style.display = 'grid';
    container.style.gap = '16px';
    container.style.gridTemplateColumns = 'repeat(auto-fit, minmax(150px, 1fr))';
    
    // Initialize answer object if needed
    if (!state.answers[step] || typeof state.answers[step] !== 'object') {
        // check if it was "Don't know" string previously
        if (state.answers[step] === "Don't know") {
             // Keep it, but UI needs to handle logic below
        } else {
             state.answers[step] = {};
        }
    }

    question.sub_fields.forEach(field => {
        const fieldWrapper = document.createElement('div');
        
        const label = document.createElement('label');
        label.textContent = field.label;
        label.style.display = 'block';
        label.style.marginBottom = '8px';
        label.style.fontWeight = '600';
        label.style.fontSize = '14px';
        
        const input = document.createElement('input');
        input.type = 'number';
        input.className = 'number-input';
        if (field.min !== undefined) input.min = field.min;
        if (field.max !== undefined) input.max = field.max;
        
        // Load existing value
        if (typeof state.answers[step] === 'object' && state.answers[step][field.id]) {
            input.value = state.answers[step][field.id];
        } else if (state.answers[step] === "Don't know") {
            input.disabled = true;
        }
        
        input.addEventListener('input', () => {
            if (typeof state.answers[step] !== 'object') state.answers[step] = {};
            state.answers[step][field.id] = input.value;
            syncStateToAgent();
            
            // Uncheck "Don't know" if present
            const dk = container.parentNode.querySelector('input[name^="dk_"]');
            if (dk) {
                dk.checked = false;
                dk.closest('.radio-option')?.classList.remove('selected');
            }
        });
        
        fieldWrapper.appendChild(label);
        fieldWrapper.appendChild(input);
        container.appendChild(fieldWrapper);
    });
    
    elements.formGroup.appendChild(container);
    
    // Add "Don't know" option if available
    if (question.options && question.options.includes("Don't know")) {
        const dkDiv = document.createElement('div');
        dkDiv.className = 'radio-option';
        dkDiv.style.marginTop = '16px';
        
        const dkCheck = document.createElement('input');
        dkCheck.type = 'checkbox';
        dkCheck.name = `dk_${step}`;
        dkCheck.id = `dk_${step}`;
        
        if (state.answers[step] === "Don't know") {
            dkCheck.checked = true;
            dkDiv.classList.add('selected');
        }
        
        const dkLabel = document.createElement('label');
        dkLabel.htmlFor = dkCheck.id;
        dkLabel.textContent = "Don't know";
        
        dkCheck.addEventListener('change', () => {
            if (dkCheck.checked) {
                state.answers[step] = "Don't know";
                dkDiv.classList.add('selected');
                // Disable inputs
                container.querySelectorAll('input').forEach(i => {
                    i.disabled = true;
                    i.value = '';
                });
            } else {
                state.answers[step] = {};
                dkDiv.classList.remove('selected');
                container.querySelectorAll('input').forEach(i => i.disabled = false);
            }
            syncStateToAgent();
        });
        
        dkDiv.appendChild(dkCheck);
        dkDiv.appendChild(dkLabel);
        elements.formGroup.appendChild(dkDiv);
    }
}

// Create Show Screen (Info only)
function createShowScreen() {
    const infoDiv = document.createElement('div');
    infoDiv.className = 'status-message info show';
    infoDiv.innerHTML = 'ℹ️ Please read the message above and click Next to continue.';
    elements.formGroup.appendChild(infoDiv);
    
    // Auto-mark answer as "VIEWED" so validation passes
    if (!state.answers[state.currentStep]) {
        state.answers[state.currentStep] = "VIEWED";
    }
}

// Handle next button
async function handleNext() {
    const currentAnswer = state.answers[state.currentStep];

    // Validate answer locally first (basic checks)
    const validation = validateAnswer(state.currentStep, currentAnswer);
    if (!validation.valid) {
        showStatus(validation.message, 'error');
        return;
    }

    elements.nextBtn.disabled = true;
    elements.nextBtn.textContent = 'Processing...';

    try {
        // Call server to validate and get next step
        const result = await submitAnswerToApi(state.currentStep, currentAnswer);
        
        if (!result.valid) {
            showStatus(result.message, 'error');
            return;
        }

        const nextStep = result.next_step;

    if (nextStep === 'TERMINATE') {
        showStatus('Based on your response, you do not qualify for this survey. Thank you for your time.', 'error');
        setTimeout(() => {
            showCompletionScreen(false);
        }, 2000);
        return;
    }

    if (nextStep === 'END') {
        showStatus('Survey completed successfully!', 'success');
        setTimeout(() => {
            showCompletionScreen(true);
        }, 1000);
        return;
    }

        // Move to next question
    state.stepHistory.push(state.currentStep);
    state.currentStep = nextStep;
    loadQuestion(nextStep);
    updateProgress(); // This will also update the comprehensive progress panel
        
        // Sync with Voice Agent if active - send FULL state including all answers
        if (state.mode === 'voice' && state.isVoiceActive && state.websocket) {
             // Sync complete state first (all answers, current step, full history)
             state.websocket.send(JSON.stringify({
                type: 'sync_state',
                step: state.currentStep,
                answers: state.answers,  // Full answers object with all previous answers
                step_history: state.stepHistory  // Complete history
            }));
            
            // Prompt agent to check context and read the new question
            setTimeout(() => {
                if (state.websocket && state.websocket.readyState === WebSocket.OPEN) {
                    state.websocket.send(JSON.stringify({
                        mime_type: 'text/plain',
                        data: 'I just answered a question manually. Please check the current state and read the question that\'s now on screen.'
                    }));
                }
            }, 100);
        }

    } catch (error) {
        console.error('Next step error:', error);
        showStatus('Error calculating next step. Please try again.', 'error');
    } finally {
        elements.nextBtn.disabled = false;
        elements.nextBtn.textContent = 'Next →';
    }
}

// Submit answer to API
async function submitAnswerToApi(currentStep, answer) {
    const response = await fetch('/api/submit-answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            current_step: currentStep,
            answer: answer,
            answers: state.answers
        })
    });
    
    if (!response.ok) throw new Error('API Error');
    return await response.json();
}

// Sync state to voice agent (used when user manually changes answers)
function syncStateToAgent() {
    if (state.mode === 'voice' && state.isVoiceActive && state.websocket && state.websocket.readyState === WebSocket.OPEN) {
        // Send complete state including all answers and full history
        state.websocket.send(JSON.stringify({
            type: 'sync_state',
            step: state.currentStep,
            answers: state.answers,  // Full answers object
            step_history: state.stepHistory  // Complete history
        }));
        console.log('[SYNC] State synced to agent after manual change');
    }
}

// Handle back button
function handleBack() {
    if (state.stepHistory.length === 0) return;
    const prevStep = state.stepHistory.pop();
    
    // We don't delete the answer, so user can edit
    state.currentStep = prevStep;
    loadQuestion(state.currentStep);
    updateProgress(); // This will also update the comprehensive progress panel

    // Sync FULL state to server so agent stays in sync with complete history
    // Also send a text message to prompt agent to check current question
    if (state.websocket && state.websocket.readyState === WebSocket.OPEN) {
        // First sync the complete state (all answers, current step, full history)
        state.websocket.send(JSON.stringify({
            type: 'sync_state',
            step: state.currentStep,
            answers: state.answers,  // Full answers object with all previous answers
            step_history: state.stepHistory  // Complete history
        }));
        
        // Then send a message to prompt agent to check context and read the current question
        setTimeout(() => {
            if (state.websocket && state.websocket.readyState === WebSocket.OPEN) {
                state.websocket.send(JSON.stringify({
                    mime_type: 'text/plain',
                    data: 'I went back to a previous question. Please check the current state and read the question that\'s now on screen.'
                }));
            }
        }, 100);
    }
}

// Validate answer
function validateAnswer(step, answer) {
    const question = surveyData[step];
    if (!question) return { valid: true }; // Should not happen

    if (!answer && question.type !== 'show') {
        return { valid: false, message: 'Please provide an answer.' };
    }

    if (question.type === 'number' || (question.type === 'number_or_unknown' && answer !== "Don't know")) {
        const num = parseInt(answer);
        if (isNaN(num)) {
            return { valid: false, message: 'Please enter a valid number' };
        }
        // Basic static validation. Server does dynamic validation (e.g. min > other_answer)
        if (typeof question.min === 'number' && num < question.min) {
            return { valid: false, message: `Number must be at least ${question.min}` };
        }
        if (typeof question.max === 'number' && num > question.max) {
            return { valid: false, message: `Number must be at most ${question.max}` };
        }
    }
    
    if (question.type === 'multiple_choice') {
        if (!answer || (Array.isArray(answer) && answer.length === 0)) {
            return { valid: false, message: 'Please select at least one option.' };
        }
    }

    return { valid: true };
}

// Toggle progress panel
function toggleProgressPanel() {
    const container = elements.surveyProgressContainer;
    const btn = elements.toggleProgressBtn;
    
    if (container.style.display === 'none') {
        container.style.display = 'block';
        btn.textContent = '▲';
        updateSurveyProgressPanel(); // Refresh when expanding
    } else {
        container.style.display = 'none';
        btn.textContent = '▼';
    }
}

// Update comprehensive survey progress panel
function updateSurveyProgressPanel() {
    if (!elements.progressQuestionsList) return;
    
    elements.progressQuestionsList.innerHTML = '';
    
    // Get all steps in order (from stepHistory + current step)
    const allSteps = [...state.stepHistory];
    if (!allSteps.includes(state.currentStep) && surveyData[state.currentStep]) {
        allSteps.push(state.currentStep);
    }
    
    // Also include any steps that have answers but aren't in history (for completeness)
    Object.keys(state.answers).forEach(step => {
        if (!allSteps.includes(step) && surveyData[step]) {
            allSteps.push(step);
        }
    });
    
    // Create question items for each step
    allSteps.forEach((step, index) => {
        const question = surveyData[step];
        if (!question) return;
        
        const isCurrent = step === state.currentStep;
        const hasAnswer = step in state.answers;
        
        const questionItem = document.createElement('div');
        questionItem.className = `progress-question-item ${isCurrent ? 'current' : ''} ${hasAnswer ? 'answered' : ''}`;
        
        const questionHeader = document.createElement('div');
        questionHeader.className = 'progress-question-header';
        
        const stepBadge = document.createElement('span');
        stepBadge.className = `progress-question-step ${isCurrent ? 'current' : ''}`;
        stepBadge.textContent = step;
        
        const questionText = document.createElement('div');
        questionText.className = 'progress-question-text';
        questionText.textContent = question.question;
        
        questionHeader.appendChild(stepBadge);
        questionHeader.appendChild(questionText);
        
        questionItem.appendChild(questionHeader);
        
        // Add options based on question type
        if (question.options && question.options.length > 0) {
            const optionsContainer = document.createElement('div');
            optionsContainer.className = 'progress-question-options';
            
            question.options.forEach(option => {
                const optionDiv = document.createElement('div');
                optionDiv.className = 'progress-option';
                
                const isSelected = checkIfOptionSelected(step, option, question.type);
                if (isSelected) {
                    optionDiv.classList.add('selected');
                }
                
                const input = document.createElement('input');
                if (question.type === 'multiple_choice') {
                    input.type = 'checkbox';
                } else {
                    input.type = 'radio';
                }
                input.value = option;
                input.checked = isSelected;
                input.disabled = !isCurrent; // Only allow editing current question
                
                input.addEventListener('change', () => {
                    handleProgressOptionChange(step, option, question.type, input.checked);
                });
                
                const label = document.createElement('label');
                label.textContent = option;
                label.style.cursor = isCurrent ? 'pointer' : 'default';
                
                optionDiv.appendChild(input);
                optionDiv.appendChild(label);
                optionsContainer.appendChild(optionDiv);
            });
            
            questionItem.appendChild(optionsContainer);
        } else if (question.type === 'number' || question.type === 'number_or_unknown' || question.type === 'text') {
            // Show answer for number/text questions
            if (hasAnswer) {
                const answerDisplay = document.createElement('div');
                answerDisplay.className = 'progress-answer-display';
                let answerText = state.answers[step];
                if (Array.isArray(answerText)) answerText = answerText.join(', ');
                answerDisplay.innerHTML = `<strong>Answer:</strong> ${answerText}`;
                questionItem.appendChild(answerDisplay);
            }
        }
        
        // Add edit button for answered questions
        if (hasAnswer && !isCurrent) {
            const editBtn = document.createElement('button');
            editBtn.className = 'progress-edit-btn';
            editBtn.textContent = 'Edit';
            editBtn.addEventListener('click', () => {
                navigateToStep(step);
            });
            questionItem.appendChild(editBtn);
        }
        
        elements.progressQuestionsList.appendChild(questionItem);
    });
}

// Check if an option is selected
function checkIfOptionSelected(step, option, questionType) {
    const answer = state.answers[step];
    if (!answer) return false;
    
    if (questionType === 'multiple_choice') {
        if (Array.isArray(answer)) {
            return answer.includes(option);
        }
        return answer === option || String(answer).includes(option);
    } else {
        return answer === option;
    }
}

// Handle option change in progress panel
function handleProgressOptionChange(step, option, questionType, isChecked) {
    if (step !== state.currentStep) {
        // Navigate to that step first
        navigateToStep(step);
        // Wait a bit for navigation, then update
        setTimeout(() => handleProgressOptionChange(step, option, questionType, isChecked), 100);
        return;
    }
    
    if (questionType === 'multiple_choice') {
        let currentAnswers = state.answers[step] || [];
        if (!Array.isArray(currentAnswers)) {
            currentAnswers = [currentAnswers];
        }
        
        if (isChecked) {
            if (!currentAnswers.includes(option)) {
                currentAnswers.push(option);
            }
        } else {
            currentAnswers = currentAnswers.filter(a => a !== option);
        }
        
        state.answers[step] = currentAnswers.length > 0 ? currentAnswers : null;
    } else {
        state.answers[step] = isChecked ? option : null;
    }
    
    // Sync state immediately
    syncStateToAgent();
    updateProgress();
    updateSurveyProgressPanel(); // Refresh panel
}

// Navigate to a specific step
function navigateToStep(step) {
    // Find step in history or add it
    if (!state.stepHistory.includes(step)) {
        // Going to a step not in history - rebuild history up to that point
        // For simplicity, just set current step and let user navigate
        state.currentStep = step;
    } else {
        // Going back to a previous step
        const stepIndex = state.stepHistory.indexOf(step);
        state.stepHistory = state.stepHistory.slice(0, stepIndex);
        state.currentStep = step;
    }
    
    loadQuestion(step);
    updateProgress();
    updateSurveyProgressPanel();
    
    // Sync with agent
    syncStateToAgent();
    if (state.websocket && state.websocket.readyState === WebSocket.OPEN) {
        setTimeout(() => {
            state.websocket.send(JSON.stringify({
                mime_type: 'text/plain',
                data: 'I navigated to a different question. Please check the current state and read the question that\'s now on screen.'
            }));
        }, 100);
    }
}

// Update progress display
function updateProgress() {
    // Since we have branching, we don't know total questions. 
    // Just show count of answered.
    const answeredCount = Object.keys(state.answers).filter(k => state.answers[k] !== null && state.answers[k] !== undefined && state.answers[k] !== '').length;
    // Estimate total? Maybe 20-30? Let's just show raw count.

    elements.progressText.textContent = `${answeredCount} questions answered`;
    
    // Calculate progress percentage (rough estimate based on answered questions)
    const estimatedTotal = Math.max(20, answeredCount + 5); // Rough estimate
    const progressPercent = Math.min(100, (answeredCount / estimatedTotal) * 100);
    elements.progressBar.style.width = `${progressPercent}%`;

    // Update answers list (recent answers)
    elements.answersList.innerHTML = '';
    // Show last 5 answers
    const recentSteps = state.stepHistory.slice(-5).reverse();
    
    recentSteps.forEach(step => {
        if (!state.answers[step]) return;
        const answerItem = document.createElement('div');
        answerItem.className = 'answer-item';
        
        let displayAnswer = state.answers[step];
        if (typeof displayAnswer === 'object' && !Array.isArray(displayAnswer)) displayAnswer = JSON.stringify(displayAnswer);
        if (Array.isArray(displayAnswer)) displayAnswer = displayAnswer.join(', ');
        
        const question = surveyData[step];
        const questionText = question ? question.question.substring(0, 50) + '...' : step;
        
        answerItem.innerHTML = `
      <div class="answer-label">${step}: ${questionText}</div>
      <div class="answer-value">${displayAnswer}</div>
    `;
        answerItem.style.cursor = 'pointer';
        answerItem.addEventListener('click', () => navigateToStep(step));
        elements.answersList.appendChild(answerItem);
    });
    
    // Update comprehensive progress panel if it's visible
    if (elements.surveyProgressContainer && elements.surveyProgressContainer.style.display !== 'none') {
        updateSurveyProgressPanel();
    }
}

// Show status message
function showStatus(message, type = 'info') {
    elements.statusMessage.textContent = message;
    elements.statusMessage.className = `status-message ${type} show`;
}

// Hide status message
function hideStatus() {
    elements.statusMessage.classList.remove('show');
}

// Download survey results
function downloadResults() {
    console.log('[DOWNLOAD] Generating survey report...');

    let report = `Otezla Chart Audit Survey - Results\n`;
    report += `Generated on: ${new Date().toLocaleString()}\n`;
    report += `-------------------------------------------\n\n`;

    Object.keys(state.answers).forEach(step => {
        const question = surveyData[step];
        const answer = state.answers[step];
        
        let qText = question ? question.question : step;
        let aText = typeof answer === 'object' ? JSON.stringify(answer) : answer;
        
        report += `[${step}] ${qText}\n`;
        report += `Answer: ${aText}\n\n`;
    });

    const blob = new Blob([report], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Otezla_Survey_Results_${state.sessionId}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    console.log('[DOWNLOAD] Report downloaded successfully');
}

// Show completion screen
function showCompletionScreen(success) {
    elements.formContent.style.display = 'none';
    elements.completionScreen.classList.add('show');

    if (!success) {
        elements.completionScreen.querySelector('.completion-icon').textContent = '✗';
        elements.completionScreen.querySelector('.completion-icon').style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
        elements.completionScreen.querySelector('.completion-title').textContent = 'Survey Terminated';
        elements.completionScreen.querySelector('.completion-message').textContent = 'You do not qualify for this survey based on the criteria. Thank you for your time.';
    } else {
        // Auto-download on success
        downloadResults();
    }
}

// Voice Mode Functions
async function startVoiceMode() {
    console.log('[VOICE] Starting voice mode');

    state.isVoiceActive = true;
    elements.startVoiceBtn.style.display = 'none';
    elements.stopVoiceBtn.style.display = 'block';
    elements.voiceIndicator.classList.add('active');
    elements.assistantStatus.textContent = 'Listening...';

    // Connect WebSocket for voice
    connectVoiceWebSocket();

    // Start audio worklets
    await startAudioWorklets();

    // Greet and ask first question
    // const greeting = "Hello Doctor, I'm your survey assistant. I'll guide you through the questions. Let's begin.";
    // speakText(greeting);
    // Don't speak automatically; let the agent drive logic.
}

function stopVoiceMode() {
    console.log('[VOICE] Stopping voice mode');

    state.isVoiceActive = false;
    elements.startVoiceBtn.style.display = 'block';
    elements.stopVoiceBtn.style.display = 'none';
    elements.voiceIndicator.classList.remove('active');
    elements.assistantStatus.textContent = 'Ready to assist';

    // Close WebSocket
    if (state.websocket) {
        state.websocket.close();
        state.websocket = null;
    }
}

function connectVoiceWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${protocol}://${window.location.host}/ws/form/${state.sessionId}?is_audio=true`;

    console.log("[VOICE] Connecting to:", wsUrl);

    state.websocket = new WebSocket(wsUrl);

    state.websocket.onopen = () => {
        console.log('[VOICE] WebSocket connected');

        // SEND HANDSHAKE with current state (including step_history for back-support)
        const handshake = {
            type: "handshake",
            step: state.currentStep,
            answers: state.answers,
            step_history: state.stepHistory
        };
        state.websocket.send(JSON.stringify(handshake));
        console.log('[VOICE] Sent handshake:', handshake);
    };

    state.websocket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleVoiceMessage(message);
    };

    state.websocket.onclose = () => {
        console.log('[VOICE] WebSocket closed');
    };

    state.websocket.onerror = (error) => {
        console.error('[VOICE] WebSocket error:', error);
    };
}


function handleVoiceMessage(message) {
    console.log('[VOICE] Received:', message);

    // Handle different message types
    if (message.mime_type === 'audio/pcm' && state.audioPlayerNode) {
        // Play audio response
        const audioData = base64ToArray(message.data);
        state.audioPlayerNode.port.postMessage(audioData);
    }

    // Handle navigation message from server (Agent drove the flow)
    if (message.type === 'navigation') {
        console.log('[VOICE] Navigation update:', message.step, 'step_history:', message.step_history);
        
        // Avoid reload loop if already on step
        if (message.step === state.currentStep) return;

        state.currentStep = message.step;
        state.answers = message.answers != null ? message.answers : state.answers;
        state.stepHistory = Array.isArray(message.step_history) ? message.step_history : state.stepHistory;

        if (message.step === 'TERMINATE') {
            showStatus('Based on your response, you do not qualify for this survey. Thank you for your time.', 'error');
            setTimeout(() => showCompletionScreen(false), 2000);
        } else if (message.step === 'END') {
            showStatus('Survey completed successfully!', 'success');
            setTimeout(() => showCompletionScreen(true), 1000);
        } else {
            loadQuestion(message.step);
            // Update UI with any answer that might be set
            if (state.answers[message.step]) {
                updateUIWithAnswer(state.answers[message.step]);
            }
            updateProgress(); // This will also update the comprehensive progress panel
        }
    }
}

// Update UI with answer (used when agent drives navigation)
function updateUIWithAnswer(answer) {
    const step = state.currentStep;
    const question = surveyData[step];
    if (!question) return;
    
    // Update UI based on question type
    if (question.type === 'choice') {
        // Find and check the radio button
        const radio = document.querySelector(`input[type="radio"][value="${answer}"]`);
        if (radio) {
            radio.checked = true;
            radio.dispatchEvent(new Event('change'));
        }
    } else if (question.type === 'multiple_choice') {
        // Check the checkboxes
        const answers = Array.isArray(answer) ? answer : [answer];
        answers.forEach(ans => {
            const checkbox = document.querySelector(`input[type="checkbox"][value="${ans}"]`);
            if (checkbox) {
                checkbox.checked = true;
                checkbox.dispatchEvent(new Event('change'));
            }
        });
    } else if (question.type === 'number' || question.type === 'number_or_unknown') {
        const input = document.querySelector('.number-input');
        if (input) {
            input.value = answer;
            input.dispatchEvent(new Event('input'));
        }
    } else if (question.type === 'text') {
        const textarea = document.querySelector('textarea');
        if (textarea) {
            textarea.value = answer;
            textarea.dispatchEvent(new Event('input'));
        }
    }

    if (message.is_output_transcript) {
        // Assistant spoke
        console.log('[ASSISTANT]:', message.data);
    }

    if (message.is_input_transcript) {
        // Doctor spoke - logging only
        console.log('[DOCTOR]:', message.data);
    }
}

function askQuestionVoice(question) {
    if (!state.websocket || !state.isVoiceActive) return;
    // We strictly let the Agent read the question using get_current_question tool.
}

function speakText(text) {
    if (!state.websocket) return;

    const content = {
        mime_type: 'text/plain',
        data: text
    };

    state.websocket.send(JSON.stringify(content));
}

async function startAudioWorklets() {
    // Import audio modules
    const { startAudioPlayerWorklet } = await import('./audio-player.js');
    const { startAudioRecorderWorklet } = await import('./audio-recorder.js');

    // Start player
    const [playerNode, playerCtx] = await startAudioPlayerWorklet();
    state.audioPlayerNode = playerNode;

    // Start recorder
    const [recorderNode, recorderCtx, stream] = await startAudioRecorderWorklet(handleAudioData);
    state.audioRecorderNode = recorderNode;
}

function handleAudioData(pcmData) {
    if (!state.websocket || !state.isVoiceActive) return;

    // Send audio to server
    const message = {
        mime_type: 'audio/pcm',
        data: arrayBufferToBase64(pcmData)
    };

    state.websocket.send(JSON.stringify(message));
}

function base64ToArray(base64) {
    const binaryString = window.atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
}

function arrayBufferToBase64(buffer) {
    let binary = '';
    const bytes = new Uint8Array(buffer);
    const len = bytes.byteLength;
    for (let i = 0; i < len; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return window.btoa(binary);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
