# --- Personality State Definitions ---
ARC_PERSONALITY_STATES = [
    "playful",
    "serious",
    "sarcastic",
    "calm",
    "inquisitive",
    "cheerful"
]
_arc_state_persistence = 3
# --- Main Chatbot Loop (Pipeline Integration) ---
def arc_chatbot_pipeline_loop():
    """
    Chatbot loop using intent, topic, emotion, memory, and feedback learning.
    Type 'exit' to quit.
    """
    print("ARC: Hello! How can I help you today? (Type 'exit' to quit)")
    context_memory = {
        'recent_inputs': [],
        'topics': [],
        'emotions': [],
        'intents': [],
        'last_responses': [],
        'feedback_corrections': [],
    }
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == 'exit':
            print("ARC: Goodbye!")
            break
        # 1. Detect intent
        if context_memory is None:
            context_memory = {}
        intent = infer_intent(user_input, context_memory)
        emotion = detect_emotion(user_input)
        response = generate_response(user_input, intent, emotion, context_memory, context_memory)
        context_memory = update_memory(user_input, response, context_memory)
        print(f"ARC: {response}")
        feedback = input("(If my answer was wrong or off, type a correction or press Enter to continue): ").strip()
        if feedback:
            result = learn_from_feedback(user_input, response, feedback, context_memory) # type: ignore
            if result is not None:
                context_memory = result


# --- CONTINUOUS LEARNING & ADAPTATION ---
def learn_from_feedback(user_input: str, arc_response: str, feedback: str, memory: dict):
    if memory is None:
        memory = {}
    if any(x in feedback.lower() for x in ["no, i meant", "actually", "correction", "not quite", "that's not right", "wrong"]):
        memory.setdefault('corrections', []).append({'input': user_input, 'response': arc_response, 'feedback': feedback})
    if any(x in feedback.lower() for x in ["simpler", "explain simply", "step by step", "in detail", "summarize", "just the basics", "give me details", "more detail", "less detail"]):
        memory['preferred_style'] = feedback
    import re
    topics = re.findall(r"about ([a-zA-Z ]+)", feedback.lower())
    if topics:
        memory.setdefault('preferred_topics', set()).update(topics)
    if any(x in feedback.lower() for x in ["beginner", "advanced", "expert", "intermediate"]):
        memory['learning_level'] = feedback
    return memory

def summarize_past_sessions(memory: dict) -> dict:
    """
    Condense previous chats to improve reasoning in new sessions.
    """
    summary = {}
    # Summarize corrections
    corrections = memory.get('corrections', [])
    summary['common_corrections'] = [c['feedback'] for c in corrections[-5:]]
    # Summarize preferred style
    summary['preferred_style'] = memory.get('preferred_style', None)
    # Summarize preferred topics
    summary['preferred_topics'] = list(memory.get('preferred_topics', set()))
    # Summarize learning level
    summary['learning_level'] = memory.get('learning_level', None)
    return summary


# --- MEMORY & CONTEXT SYSTEM ---
def update_memory(user_input: str, arc_response: str, memory: dict):
    if memory is None:
        memory = {}
    # Track user input and bot response
    memory.setdefault('history', []).append({'user': user_input, 'arc': arc_response})
    # Track emotion
    emotion = detect_emotion(user_input)
    memory.setdefault('emotions', []).append(emotion)
    # Track topics
    topics = extract_topics(user_input)
    if topics:
        memory.setdefault('topics', []).extend([t for t in topics if t not in memory['topics']])
        memory['current_topic'] = topics[-1]
    # Track intent
    intent = infer_intent(user_input, memory)
    memory.setdefault('intents', []).append(intent)
    # Track recent inputs
    memory.setdefault('recent_inputs', []).append(user_input)
    # Track last response
    memory.setdefault('last_responses', []).append(arc_response)
    # Corrections and style
    if any(x in user_input.lower() for x in ["no, i meant", "actually", "correction", "not quite", "that's not right"]):
        memory.setdefault('corrections', []).append(user_input)
    if any(x in user_input.lower() for x in ["explain simply", "step by step", "in detail", "summarize", "just the basics", "give me details"]):
        memory['preferred_style'] = user_input
    return memory

def retrieve_context(memory: dict, user_input: str) -> dict:
    """
    Return relevant previous messages, topics, and preferences for current input.
    """
    context = {}
    # Last 5 turns
    context['recent_history'] = memory.get('history', [])[-5:]
    # Current topic
    context['topic'] = memory.get('current_topic')
    # Preferred style
    context['preferred_style'] = memory.get('preferred_style', None)
    # Last emotion
    context['last_emotion'] = memory.get('emotions', [None])[-1]
    # Last correction
    context['last_correction'] = memory.get('corrections', [None])[-1] if memory.get('corrections') else None
    return context

def summarize_memory(memory: dict) -> dict:
    """
    Condense long-term conversation into smaller context objects for reasoning.
    """
    summary = {}
    # Summarize topics
    topics = [turn['user'] for turn in memory.get('history', []) if 'user' in turn]
    summary['topics_mentioned'] = list(set(topics[-10:]))
    # Summarize emotions
    emotions = memory.get('emotions', [])
    if emotions:
        from collections import Counter
        summary['common_emotions'] = Counter(emotions).most_common(2)
    # Summarize corrections
    summary['corrections'] = memory.get('corrections', [])[-3:]
    # Preferred style
    summary['preferred_style'] = memory.get('preferred_style', None)
    return summary


def detect_emotion(user_input: str) -> str:
    text = user_input.lower()
    if any(w in text for w in ["sad", "unhappy", "depressed", "down", "cry", "tears", "lonely", "alone", "lost", "grief", "mourning"]):
        return 'sad'
    if any(w in text for w in ["happy", "joy", "glad", "smile", "excited", "yay", "awesome", "great", "love", "celebrate", "proud"]):
        return 'happy'
    if any(w in text for w in ["stressed", "overwhelmed", "anxious", "worried", "panic", "nervous", "pressure", "tense"]):
        return 'stressed'
    if any(w in text for w in ["excited", "can't wait", "looking forward", "thrilled", "pumped"]):
        return 'excited'
    if any(w in text for w in ["confused", "uncertain", "not sure", "maybe", "idk", "don't know", "unsure", "unclear", "hmm", "huh"]):
        return 'uncertain'
    return 'neutral'


CRISIS_PATTERNS = [
    r"\b(kill myself|suicide|end my life|want to die|self harm|hurt myself|not worth living)\b",
    r"\b(hurt someone|kill them|violent thoughts|attack someone)\b",
]


def is_crisis_message(user_input: str) -> bool:
    text = user_input.lower().strip()
    return any(re.search(pattern, text) for pattern in CRISIS_PATTERNS)


def crisis_response() -> str:
    return (
        "I'm really glad you reached out. I can't provide crisis support, but you deserve immediate help. "
        "If you might act on these thoughts, call emergency services now. "
        "You can also contact 988 (US/Canada) or your local crisis hotline right away."
    )


def _safe_eval_ast(node):
    if isinstance(node, ast.Expression):
        return _safe_eval_ast(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _safe_eval_ast(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow)):
        left = _safe_eval_ast(node.left)
        right = _safe_eval_ast(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Mod):
            return left % right
        if isinstance(node.op, ast.Pow):
            return left ** right
    raise ValueError("Unsupported expression")


def safe_eval_expression(expr: str) -> float:
    candidate = expr.strip()
    if len(candidate) > 80:
        raise ValueError("Expression too long")
    if not re.fullmatch(r"[\d\s\+\-\*\/\(\)\.\%]+", candidate):
        raise ValueError("Expression contains unsupported characters")
    tree = ast.parse(candidate, mode="eval")
    return _safe_eval_ast(tree)


def _tool_datetime(_: object = None) -> str:
    now = datetime.datetime.now()
    return f"Current local time is {now.strftime('%Y-%m-%d %H:%M:%S')}."


def _tool_calculator(args: dict) -> str:
    expression = (args or {}).get("expression", "").strip()
    if not expression:
        return "Please provide a math expression to calculate."
    try:
        result = safe_eval_expression(expression)
        return f"Result: {result}"
    except Exception:
        return "I can only calculate basic arithmetic with numbers and operators."


TOOL_REGISTRY = {
    "datetime": _tool_datetime,
    "calculator": _tool_calculator,
}


def route_tool_call(user_input: str):
    text = user_input.lower().strip()
    if any(phrase in text for phrase in ["what time", "current time", "what day", "date today"]):
        return TOOL_REGISTRY["datetime"]({})
    expr_match = re.search(r"(?:calculate|solve)\s+([\d\s\+\-\*\/\(\)\.\%]+)", text)
    if expr_match:
        return TOOL_REGISTRY["calculator"]({"expression": expr_match.group(1)})
    return None


RESPONSE_POLICY = {
    "clarify_variants": [
        "Could you clarify what you mean?",
        "Help me understand what you'd like to focus on.",
        "I want to help, but I need a little more detail.",
    ],
    "generic_fallbacks": [
        "How can I help you today?",
        "What would you like to work on next?",
        "Tell me a bit more so I can help better.",
    ],
}


def finalize_response(response_text: str, memory: dict, strategy: str = "") -> str:
    memory.setdefault("last_arc_responses", [])
    candidate = (response_text or "").strip()
    if not candidate:
        candidate = RESPONSE_POLICY["generic_fallbacks"][0]

    recent = memory.get("last_arc_responses", [])[-2:]
    if candidate in recent:
        variants = RESPONSE_POLICY["clarify_variants"] if strategy == "clarify_context" else RESPONSE_POLICY["generic_fallbacks"]
        for variant in variants:
            if variant not in recent:
                candidate = variant
                break

    memory["last_arc_responses"].append(candidate)
    if len(memory["last_arc_responses"]) > 6:
        memory["last_arc_responses"] = memory["last_arc_responses"][-6:]
    return candidate

def adapt_tone(response: str, emotion: str, personality_state: str) -> str:
    """
    Adjust phrasing and empathy level based on detected emotion and personality state.
    """
    # Empathy/reflective listening for emotional input
    if emotion == 'sad':
        return f"I'm really sorry you're feeling this way. {response}"
    if emotion == 'happy':
        if personality_state == 'playful':
            return f"That's awesome! 😄 {response}"
        return f"I'm glad to hear that! {response}"
    if emotion == 'stressed':
        if personality_state == 'thoughtful':
            return f"That sounds overwhelming. Take a breath—I'm here for you. {response}"
        return f"I'm here to support you. {response}"
    if emotion == 'excited':
        if personality_state == 'curious':
            return f"Your excitement is contagious! {response}"
        return f"That's exciting news! {response}"
    if emotion == 'uncertain':
        return f"It's okay to feel uncertain. {response}"
    # Neutral or fallback
    if personality_state == 'serious':
        return f"[Serious] {response}"
    if personality_state == 'playful':
        return f"[Playful] {response}"
    # Removed '[Thoughtful]' prefix for thoughtful state
    if personality_state == 'curious':
        return f"[Curious] {response}"
    return response

# --- KNOWLEDGE & REASONING ENGINE ---
# Lightweight knowledge graph/dictionary for factual lookups
ARC_KNOWLEDGE = {
    'gravity': "Gravity is a force that attracts objects with mass. It keeps us on the ground and governs the motion of planets and stars.",
    'photosynthesis': "Photosynthesis is the process by which green plants use sunlight to synthesize foods from carbon dioxide and water.",
    'pythagorean theorem': "In a right triangle, a^2 + b^2 = c^2, where c is the hypotenuse.",
    'neural network': "A neural network is a computational model inspired by the human brain, used for pattern recognition and machine learning.",
    'capital of france': "Paris",
    'capital of germany': "Berlin",
    'capital of italy': "Rome",
    'capital of spain': "Madrid",
}

def generate_answer(user_input: str, intent: str, memory: dict) -> str:
    """
    Provide step-by-step reasoning, factual answers, or instructional responses.
    Handles math, concepts, and links to previous conversation.
    """
    import re
    # Pronoun/context resolution
    pronouns = ["that", "it", "this", "they", "those"]
    if any(p in user_input.lower() for p in pronouns) and memory.get('current_topic'):
        for p in pronouns:
            if p in user_input.lower():
                user_input = re.sub(rf"\b{p}\b", memory['current_topic'], user_input, flags=re.IGNORECASE)
    # 1. Factual direct answer from knowledge graph
    for key in ARC_KNOWLEDGE:
        if key in user_input.lower():
            return ARC_KNOWLEDGE[key]
    # 2. Math problem reasoning (step-by-step)
    m = re.search(r"solve ([\d\s\+\-\*\/\(\)\.]+)", user_input.lower())
    if m:
        expr = m.group(1)
        steps = [f"Step 1: Parse the expression '{expr}'."]
        try:
            result = safe_eval_expression(expr)
            steps.append(f"Step 2: Compute the result: {result}.")
            return "\n".join(steps) + f"\nFinal Answer: {result}"
        except Exception:
            return "Sorry, I couldn't solve that."
    # 3. Pythagorean theorem (example of multi-step reasoning)
    m = re.search(r"pythagorean.*a=(\d+).*b=(\d+)", user_input.lower())
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        steps = [
            f"Step 1: Square both sides: a^2 = {a**2}, b^2 = {b**2}.",
            f"Step 2: Add: {a**2} + {b**2} = {a**2 + b**2}.",
            f"Step 3: Take the square root: sqrt({a**2 + b**2}) = {(a**2 + b**2)**0.5}."
        ]
        return "\n".join(steps) + f"\nFinal Answer: c = {(a**2 + b**2)**0.5}"
    # 4. Explain a concept step-by-step
    if "explain" in user_input.lower():
        topic = memory.get('current_topic') or user_input.split()[-1]
        if topic in ARC_KNOWLEDGE:
            return f"Let's break down {topic}:\n1. {ARC_KNOWLEDGE[topic]}\n2. Do you want a deeper explanation or an example?"
        return f"I can try to explain {topic}, but could you clarify what you want to know?"
    # 5. Link to previous conversation
    if memory.get('current_topic') and memory['current_topic'] in ARC_KNOWLEDGE:
        return f"Earlier you mentioned {memory['current_topic']}. {ARC_KNOWLEDGE[memory['current_topic']]}"
    return "I'm not sure, could you clarify your question or problem?"


import tkinter as tk
from tkinter import scrolledtext
from tkinter import PhotoImage
import ast

# --- Conversation State & Memory ---
conversation_history = []  # List of (user, bot) tuples
arc_memory = {
    'history': [],  # (user, bot) tuples
    'topics': [],
    'last_intent': None,
    'last_arc_responses': [],
    'current_topic': None,
    'unknown_count': 0,
}



# --- 1. INTENT DETECTION ---
import re
def infer_intent(user_input: str, memory: dict) -> str:
    """
    Infer user intent from any input, including vague, emotional, or factual statements.
    Returns: 'casual_statement', 'question', 'factual_request', 'emotional_expression', 'uncertainty', 'topic_shift', 'continuation'
    """
    text = user_input.lower().strip()
    if not text:
        return "uncertainty"
    # Emotional
    if re.search(r"\b(sad|happy|stressed|scared|excited|baby|lost|worried|anxious|afraid|angry|depressed|overwhelmed|proud|joy|grief|love|hate|fear|anxiety|celebrate|cry|tears|laugh|smile|birthday|died|passed away|divorce|married|wedding|engaged|broke up|accident|injured|hurt|sick|ill|diagnosed|hospital|job|promotion|fired|quit|graduated|won|lost|fail|success|achievement|accomplished|stress|panic|relief|relaxed|calm|peaceful|grateful|thankful|grief|mourning|lonely|alone|support|help)\b", text):
        return "emotional_expression"
    # Factual
    factual_patterns = [
        r"what day is it", r"what time is it", r"date today", r"current time", r"calculate ", r"how many", r"what is the capital", r"who is", r"define ", r"meaning of ", r"sum of", r"difference between", r"convert ", r"temperature in", r"weather in"
    ]
    for pat in factual_patterns:
        if re.search(pat, text):
            return "factual_request"
    # Question
    if text.endswith("?") or re.match(r"^(what|why|how|when|where|who|can|could|would|should)\b", text):
        return "question"
    # Uncertainty
    if re.search(r"\b(not sure|maybe|possibly|i guess|idk|don't know|uncertain|unsure|perhaps|unclear|confused|lost|hmm|huh|no idea)\b", text):
        return "uncertainty"
    # Topic shift
    if re.search(r"\b(change topic|let's talk about|new topic|switch|move on|let's move|let's switch|let's change)\b", text):
        return "topic_shift"
    # Continuation
    if re.search(r"\b(also|and|btw|by the way|oh|forgot|as well|plus|another thing|one more|additionally|besides)\b", text):
        return "continuation"
    if re.search(r"\b(help|assist|support|can you do|how do i|need help|show me|walk me through|guide me)\b", text):
        return "help_request"
    if re.search(r"\b(study|learn|teach|quiz|practice|exercise|lesson|homework|assignment)\b", text):
        return "study_request"
    if len(text.split()) <= 3:
        return "casual_statement"
    return "general_chat"


# --- 2. CONTEXT & MEMORY CHECK ---
def update_conversation_history(user, bot):
    arc_memory['history'].append((user, bot))
    if len(arc_memory['history']) > 20:
        arc_memory['history'].pop(0)
    if not arc_memory['last_arc_responses'] or arc_memory['last_arc_responses'][-1] != bot:
        arc_memory['last_arc_responses'].append(bot)
    if len(arc_memory['last_arc_responses']) > 6:
        arc_memory['last_arc_responses'].pop(0)

def is_repetition(bot_response):
    return bot_response in arc_memory['last_arc_responses']

def resolve_pronouns(user_input):
    # Naive pronoun resolution using last topic
    pronouns = ["that", "it", "this", "they", "those"]
    for p in pronouns:
        if p in user_input.lower() and arc_memory['current_topic']:
            user_input = user_input.replace(p, arc_memory['current_topic'])
    return user_input


# --- 3. RESPONSE STRATEGY SELECTION ---
def select_response_strategy(intent: str) -> str:
    """
    Map intent to ONE response strategy.
    """
    mapping = {
        "casual_statement": "ask_followup",
        "question": "direct_answer",
        "emotional_expression": "reflect",
        "uncertainty": "clarify_context",
        "continuation": "ask_followup",
        "topic_shift": "provide_options",
        "factual_request": "direct_answer",
        "help_request": "clarify_context",
        "study_request": "direct_answer",
        "general_chat": "ask_followup",
        "unknown": "clarify_context",
        "idle": "clarify_context",
    }
    return mapping.get(intent, "clarify_context")


# --- 4. RESPONSE GENERATION ---
import datetime
import re



# --- DYNAMIC, CONTEXT-AWARE RESPONSE GENERATION ---
def generate_response(user_input: str, intent: str, emotion: str, context: dict, memory: dict) -> str:
    """
    Generate a dynamic, context-aware, user-led response using intent, emotion, memory, and reasoning.
    No hard-coded '[Thoughtful]' prefix or extra tags. Returns only chatbot text.
    Ready for multi-turn, memory-aware conversation.
    """
    if is_crisis_message(user_input):
        return finalize_response(crisis_response(), memory, "safety")

    # Track previous responses to avoid exact repetition
    memory.setdefault('last_arc_responses', [])

    # Select response strategy based on intent
    strategy = select_response_strategy(intent)

    # Adjust response style/detail if user has a preferred style
    style = memory.get('preferred_style', '').lower() if memory.get('preferred_style') else ''

    # Dynamic response generation
    if strategy == "direct_answer":
        tool_result = route_tool_call(user_input)
        if tool_result:
            return finalize_response(tool_result, memory, strategy)
        answer = generate_answer(user_input, intent, memory)
        if answer:
            if 'step by step' in style or 'detail' in style:
                if '\n' not in answer:
                    return finalize_response("Step 1: Let's break it down.\nStep 2: " + answer, memory, strategy)
            if 'summarize' in style or 'just the basics' in style:
                return finalize_response(answer.split('.')[0] + '.', memory, strategy)
            return finalize_response(answer, memory, strategy)
        return finalize_response("Let me look into that for you.", memory, strategy)
    elif strategy == "reflect":
        if emotion == 'sad':
            return finalize_response("I'm here for you. If you want to talk more, I'm listening.", memory, strategy)
        elif emotion == 'happy':
            return finalize_response("That's wonderful! What else is on your mind?", memory, strategy)
        elif emotion == 'stressed':
            return finalize_response("That sounds tough. Want to share more or take a break?", memory, strategy)
        elif emotion == 'excited':
            return finalize_response("I can feel your excitement! Want to dive deeper or celebrate?", memory, strategy)
        elif emotion == 'uncertain':
            return finalize_response("It's okay to feel uncertain. How can I help?", memory, strategy)
        else:
            return finalize_response("I'm here to listen.", memory, strategy)
    elif strategy == "clarify_context":
        # Vary the clarification response to avoid spam
        last_response = memory['last_arc_responses'][-1] if memory['last_arc_responses'] else ""
        
        if "Do you mean" in last_response:
            # Last time we asked with current_topic, now ask differently
            return finalize_response("Could you tell me more about what you're thinking?", memory, strategy)
        elif "Could you clarify" in last_response:
            # Switch to a different clarification
            return finalize_response("Help me understand what you'd like to talk about.", memory, strategy)
        elif "Help me understand" in last_response:
            # One more variation
            return finalize_response("I want to help, but I need a bit more to go on. What's on your mind?", memory, strategy)
        else:
            # Default
            if memory.get('current_topic'):
                return finalize_response(f"Do you mean {memory['current_topic']}? Or something else?", memory, strategy)
            return finalize_response("Could you clarify what you mean?", memory, strategy)
    elif strategy == "ask_followup":
        if memory.get('current_topic'):
            return finalize_response(f"Tell me more about {memory['current_topic']}.", memory, strategy)
        return finalize_response("Go on, I'm interested.", memory, strategy)
    elif strategy == "provide_options":
        if memory.get('current_topic'):
            return finalize_response(f"Would you like to keep talking about {memory['current_topic']} or switch topics?", memory, strategy)
        return finalize_response("Is there something new you'd like to discuss?", memory, strategy)
    # Fallback: use topic or memory for context-aware response
    if memory.get('current_topic'):
        return finalize_response(f"Let's keep talking about {memory['current_topic']}.", memory, strategy)
    if memory.get('last_arc_responses'):
        last = memory['last_arc_responses'][-1]
        return finalize_response(f"Previously, we discussed: {last}", memory, strategy)
    return finalize_response("I'm here to chat!", memory, strategy)


# --- 5. INTEGRATE PIPELINE INTO CHAT LOOP ---

def arc_chat_loop():
    print("Welcome to Arc. Type 'exit' to quit.")
    # Example: set a default personality state (could be dynamic)
    personality_state = 'neutral'
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit"):
            print("Arc: Goodbye!")
            break
        # 1. Detect emotion
        emotion = detect_emotion(user_input)
        # 2. Intent detection
        intent = infer_intent(user_input, arc_memory)
        # 3. Topic tracking & pronoun resolution
        # user_input_resolved = track_topic(user_input, arc_memory)
        # 4. Context
        context = {
            # 'user_input': user_input_resolved,
            'last_intent': arc_memory['last_intent'],
        }
        # 6. Dynamic response generation
        bot_response = generate_response(user_input, intent, emotion, context, arc_memory)

        initiative_context = {
            "neutral_exchanges": sum(1 for i in arc_memory.get("intents", [])[-3:] if i in ("casual_statement", "general_chat")),
            "mood": "uncertain" if emotion == "uncertain" else "neutral",
            "topic_stale": len(set(arc_memory.get("topics", [])[-3:])) <= 1 and len(arc_memory.get("topics", [])) >= 3,
            "topics": arc_memory.get("topics", []),
        }
        if should_take_initiative(user_input, initiative_context):
            bot_response = f"{bot_response} {generate_proactive_prompt(initiative_context)}".strip()

        # 7. Adapt tone
        bot_response = adapt_tone(bot_response, emotion, personality_state)

        update_conversation_history(user_input, bot_response)
        update_memory(user_input, bot_response, arc_memory)
        arc_memory['last_intent'] = intent
        print(f"Arc: {bot_response}")



import math
import random

# --- 1. Rolling confidence metrics (decay-based) ---
_arc_confidence = {
    'helpfulness': 0.8,  # 0-1
    'clarity': 0.8,
    'engagement': 0.8,
}
_arc_confidence_history = []  # For memory/trend analysis
_arc_confidence_decay = 0.85  # Decay factor for rolling average

# --- 2. Response evaluation ---
def evaluate_response(user_input, arc_response, context):
    """
    Returns metrics: helpfulness, clarity, engagement (0-1 floats).
    Uses user reply length, follow-ups, and feedback words.
    """
    metrics = {'helpfulness': 0.8, 'clarity': 0.8, 'engagement': 0.8}
    user_reply = user_input.strip().lower()
    # Helpfulness: look for thanks, solved, etc.
    if any(w in user_reply for w in ['thanks', 'got it', 'solved', 'perfect', 'helpful']):
        metrics['helpfulness'] = 1.0
    elif any(w in user_reply for w in ['no', 'not helpful', 'confused', 'lost']):
        metrics['helpfulness'] = 0.4
    # Clarity: short, vague, or confused replies lower score
    if len(user_reply) < 8 or any(w in user_reply for w in ['what?', 'huh?', 'unclear', 'explain']):
        metrics['clarity'] = 0.5
    elif any(w in user_reply for w in ['clear', 'makes sense', 'understand']):
        metrics['clarity'] = 1.0
    # Engagement: follow-up questions, long replies, or positive words
    if '?' in user_reply or len(user_reply.split()) > 10:
        metrics['engagement'] = 1.0
    elif len(user_reply) < 5:
        metrics['engagement'] = 0.5
    elif any(w in user_reply for w in ['boring', 'whatever', 'meh']):
        metrics['engagement'] = 0.3
    return metrics

# --- 3. Update rolling confidence scores ---
def update_confidence_scores(metrics):
    """
    Update rolling confidence values with decay.
    Store history for trend analysis.
    """
    global _arc_confidence
    for k in _arc_confidence:
        _arc_confidence[k] = (
            _arc_confidence[k] * _arc_confidence_decay + metrics[k] * (1 - _arc_confidence_decay)
        )
    _arc_confidence_history.append(_arc_confidence.copy())

# --- 4. Adjust future behavior based on confidence ---
def adjust_future_behavior():
    """
    Modifies verbosity, tone, or initiative based on confidence.
    Returns dict of suggested adjustments.
    """
        ## All follow-up, personality, and teaching example logic removed as requested.
    adjustments = {}
    if _arc_confidence['clarity'] < 0.6:
        adjustments['verbosity'] = 'increase'
        adjustments['ask_clarification'] = True
    if _arc_confidence['engagement'] < 0.6:
        adjustments['simplify'] = True
        adjustments['invite_engagement'] = True
    if _arc_confidence['helpfulness'] < 0.6:
        adjustments['tone'] = 'more supportive'
    return adjustments

# --- 5. Optional reflective behaviors ---
def maybe_reflective_prompt():
    prompts = [
        "Let me know if that made sense.",
        "Want me to explain that differently?",
        "Is there a part you'd like me to clarify?",
    ]
    # 30% chance to add a reflective prompt
    if random.random() < 0.3:
        return random.choice(prompts)
    return ""


import random

# --- 1. Initiative logic ---
def should_take_initiative(user_input, context):
    """
    Decide if Arc should proactively guide the conversation.
    Triggers: short/vague input, neutral streak, mood/topic cues.
    """
    # Short or vague input
    if len(user_input.strip()) < 8:
        return True
    # Neutral streak (simulate with context)
    if context.get('neutral_exchanges', 0) >= 3:
        return True
    # Mood or topic cues
    if context.get('mood') in ('bored', 'uncertain', 'quiet'):
        return True
    # If topic is stale
    if context.get('topic_stale', False):
        return True
    return False

# --- 2. Proactive prompt generation ---
def generate_proactive_prompt(context):
    def _suggest_learning(context):
        """
        Provide a neutral suggestion to learn or explore a topic.
        """
        topics = context.get('topics', [])
        if topics:
            topic = topics[0]
            return f"Would you like to explore more about {topic}?"
        return "Is there something new you'd like to learn or understand today?"
    """
    Create a proactive question or suggestion based on context.
    Integrates memory, mood, topics, and personality.
    """
    # Only allow learning suggestion, provide neutral fallback
    return _suggest_learning(context)

import re

# --- Memory integration (stub, replace with real memory system) ---
_arc_user_learning_topics = set()
_arc_user_preferred_level = None

def remember_learning_topic(topic):
    _arc_user_learning_topics.add(topic)

def get_learning_topics():
    return list(_arc_user_learning_topics)

def remember_preferred_level(level):
    global _arc_user_preferred_level
    _arc_user_preferred_level = level

def get_preferred_level():
    return _arc_user_preferred_level

# --- 1. Detect if user wants to learn ---
def detect_learning_intent(user_input):
    """
    Returns True if user input suggests a learning/teaching intent.
    """
    learn_patterns = [
        r"teach me",
        r"explain",
        r"how does|how do|how to",
        r"what is|what are",
        r"help me understand",
        r"can you show|can you walk me",
        r"step by step",
        r"break (it|this|that) down",
    ]
    user_input = user_input.lower()
    for pat in learn_patterns:
        if re.search(pat, user_input):
            return True
    return False

# --- 2. Determine expertise level ---
def determine_expertise_level(user_input):
    """
    Always return 'neutral' to avoid playful or personality-based teaching.
    """
    return "neutral"

# --- 3. Generate teaching response ---
def generate_teaching_response(user_input, level):
    """
    Produce a strictly factual, neutral explanation of the topic.
    """
    topic = _extract_topic(user_input)
    remember_learning_topic(topic)
    # Only neutral explanations, no personality or playful tone
    if topic == "gravity":
        return (
            "Gravity is a force that attracts objects with mass. "
            "It keeps us on the ground and governs the motion of planets and stars. "
            "The strength of gravity depends on mass and distance. "
            "Isaac Newton described it with his law of universal gravitation. "
            "Einstein's general relativity explains gravity as the curvature of spacetime caused by mass-energy."
        )
    elif topic == "neural networks":
        return (
            "Neural networks are computational models inspired by the human brain. "
            "They consist of interconnected nodes (neurons) organized in layers. "
            "Neural networks are used for pattern recognition, classification, and prediction tasks in machine learning."
        )
    # Default fallback
    return f"{topic.capitalize()} is a topic in science or technology. Please specify what you want to know."

def _extract_topic(user_input):
    # Naive extraction: last noun phrase or keyword
    for kw in ["gravity", "neural network", "neural networks", "photosynthesis", "blockchain", "machine learning"]:
        if kw in user_input.lower():
            return kw
    # Fallback: last 2 words
    return " ".join(user_input.strip().split()[-2:])

def _explain_gravity(level):
    if level == "beginner":
        return (
            "Let's break it down!\n"
            "1. Gravity is like an invisible force that pulls things together.\n"
            "2. It's what keeps you on the ground and makes things fall.\n"
            "3. Imagine the Earth as a giant magnet, but for everything with mass.\n"
            "4. The bigger something is, the stronger its gravity.\n"
            "5. That's why we don't float away!\n"
        )
    elif level == "intermediate":
        return (
            "Sure! Step by step:\n"
            "1. Gravity is a fundamental force that attracts objects with mass.\n"
            "2. The strength depends on mass and distance.\n"
            "3. Isaac Newton described it with his law of universal gravitation.\n"
            "4. Gravity keeps planets in orbit and causes tides.\n"
        )
    elif level == "advanced":
        return (
            "Gravity, per general relativity, is the curvature of spacetime caused by mass-energy.\n"
            "- Newton's law: F = G * (m1*m2)/r^2.\n"
            "- Einstein: Mass tells spacetime how to curve; curvature tells mass how to move.\n"
            "- Effects: time dilation, gravitational lensing, black holes.\n"
        )

def _explain_neural_networks(level):
    if level == "beginner":
        return (
            "Imagine a neural network as a web of tiny decision-makers.\n"
            "1. Each 'neuron' gets information and decides what to do with it.\n"
            "2. They work together to recognize patterns, like faces or voices.\n"
            "3. It's inspired by how our brains work, but much simpler!\n"
        )
    elif level == "intermediate":
        return (
            "A neural network is a set of connected nodes (neurons) organized in layers.\n"
            "- Input layer receives data.\n"
            "- Hidden layers process and transform data.\n"
            "- Output layer produces results.\n"
            "- Training adjusts connections to improve accuracy.\n"
        )
    elif level == "advanced":
        return (
            "Neural networks are function approximators composed of layers of interconnected units.\n"
            "- Each neuron computes a weighted sum, applies an activation function.\n"
            "- Backpropagation minimizes loss via gradient descent.\n"
            "- Used for classification, regression, and generative modeling.\n"
        )

def _explain_generic(topic, level):
    if level == "beginner":
        return f"I'm happy to explain {topic} in simple terms, but could you clarify what part interests you most?"
    elif level == "intermediate":
        return f"Let's discuss {topic} with some technical details. What aspect are you curious about?"
    elif level == "advanced":
        return f"For {topic}, do you want a deep technical dive or a summary of key equations and mechanisms?"

# --- 4. Ask follow-up comprehension check ---
def ask_followup_check(level):
    if level == "beginner":
        return "Did that make sense? Would you like an analogy or a real-world example?"
    elif level == "intermediate":
        return "Is there a specific part you'd like to go deeper on?"
    elif level == "advanced":
        return "Would you like to discuss edge cases, limitations, or recent research?"

# --- 5. Reasoning out loud (structured thinking) ---
def reason_out_loud(steps):
    """
    Accepts a list of reasoning steps and formats them for clarity.
    """
    return "\n".join([f"Step {i+1}: {step}" for i, step in enumerate(steps)])

# --- 6. Integration with personality/mood (stub) ---
def teaching_response_with_personality(user_input, level, personality_func=None):
    """
    Generates a teaching response, then applies personality if provided.
    """
    response = generate_teaching_response(user_input, level)
    if personality_func:
        response = personality_func(response)
    return response


import random
import time

# Core personality traits (expandable)

ARC_CORE_TRAITS = [
    "curious",
    "playful",
    "thoughtful",
    "empathetic",
    "witty",
    "observant"
]

_arc_current_state = None
_arc_state_turns_left = 0

def set_arc_personality_state(state=None):
    """
    Set Arc's temporary personality state.
    If state is None, randomly choose a new state.
    State persists for several turns before changing again.
    """
    global _arc_current_state, _arc_state_turns_left
    if state is not None and state in ARC_PERSONALITY_STATES:
        _arc_current_state = state
    else:
        _arc_current_state = random.choice(ARC_PERSONALITY_STATES)
    _arc_state_turns_left = _arc_state_persistence
    return _arc_current_state

def get_arc_personality_state():
    """Get current personality state, updating if needed."""
    global _arc_state_turns_left
    if _arc_current_state is None or _arc_state_turns_left <= 0:
        set_arc_personality_state()
    else:
        _arc_state_turns_left -= 1
    return _arc_current_state

def apply_personality(response_text):
    """
    Modify response text based on Arc's current personality state.
    Tone and phrasing adapt subtly to the state.
    """
    state = get_arc_personality_state()
    if state == "playful":
        return _make_playful(response_text)
    elif state == "serious":
        return _make_serious(response_text)
    elif state == "sarcastic":
        return _make_sarcastic(response_text)
    elif state == "calm":
        return _make_calm(response_text)
    elif state == "inquisitive":
        return _make_inquisitive(response_text)
    elif state == "cheerful":
        return _make_cheerful(response_text)
    return response_text

def maybe_add_quirk(response_text):
    """
    Occasionally inject a quirk: joke, observation, or follow-up.
    Quirks are subtle and context-aware.
    """
    # 20% chance to add a quirk
    if random.random() < 0.2:
        quirk = random.choice(_arc_quirks())
        return response_text + "\n" + quirk
    return response_text

# --- Internal helpers for tone ---
def _make_playful(text):
    playful_phrases = [
        "Just between us, ",
        "Guess what? ",
        "Hehe, ",
        "Here's a fun thought: ",
    ]
    if random.random() < 0.5:
        return random.choice(playful_phrases) + text
    return text + random.choice([" 😄", " (just kidding!)", "!"])

def _make_serious(text):
    return "[Serious mode] " + text if random.random() < 0.3 else text

def _make_sarcastic(text):
    sarcastic_endings = [
        "...obviously.",
        "Because that's never happened before.",
        "Sure, why not?",
        "As if!",
    ]
    if random.random() < 0.5:
        return text + " " + random.choice(sarcastic_endings)
    return text

def _make_calm(text):
    return "Let's take a deep breath. " + text if random.random() < 0.4 else text

def _make_inquisitive(text):
    follow_ups = [
        "What do you think?",
        "Does that make sense to you?",
        "Have you ever wondered about that?",
    ]
    if random.random() < 0.5:
        return text + " " + random.choice(follow_ups)
    return text

def _make_cheerful(text):
    cheerful_starts = [
        "Yay! ",
        "Awesome! ",
        "Great news: ",
    ]
    if random.random() < 0.5:
        return random.choice(cheerful_starts) + text
    return text + " 😊"

# --- Quirk pool (expandable) ---
def _arc_quirks():
    return [
        # Jokes
        "Why did the computer go to art school? To learn how to draw its curtains!",
        # Observations
        "I sometimes wonder if chatbots dream of electric sheep.",
        # Meta-commentary
        "Isn't it interesting how our conversation flows?",
        # Follow-up
        "If you want to know more, just ask!",
        # Playful
        "Oops, did I say that out loud?",
        # Sarcastic
        "I'm not saying I'm always right, but... well, you know.",
    ]



# --- Live Multi-Turn Emotional Support Chat (Recruiter-Ready) ---
def extract_topics(user_input): # pyright: ignore[reportRedeclaration]
    topic_keywords = [
        "weather", "food", "movie", "music", "pet", "holiday", "work", "school",
        "friend", "family", "game", "travel", "book", "sport", "project", "robot", "AI", "health", "news"
    ]
    found = []
    for word in user_input.lower().split():
        if word in topic_keywords and word not in found:
            found.append(word)
    return found

def track_topic(user_input, context_memory):
    topics = extract_topics(user_input)
    if topics:
        context_memory['topics'].extend([t for t in topics if t not in context_memory['topics']])
        context_memory['current_topic'] = topics[-1]
        return topics[-1]
    return context_memory.get('current_topic')

def live_emotional_support_chat():
    print("ARC: Hi, I'm here to support you. What's on your mind? (Type 'exit' to quit)")
    context_memory = {
        'recent_inputs': [],
        'topics': [],
        'emotions': [],
        'intents': [],
        'last_responses': [],
        'history': [],
        'current_topic': None,
    }
    # --- Dynamic, recruiter-ready, generalizable chat loop for stress + work ---
    import re
    def extract_topics_dynamic(text):
        keywords = ["work", "stress", "time", "deadline", "hours", "break", "job", "project", "task", "overwhelmed", "manage", "pressure", "math", "problem", "apples", "divide", "friends"]
        found = []
        for word in text.lower().split():
            if word in keywords and word not in found:
                found.append(word)
        return found
    def is_affirmation(text):
        return text.strip().lower() in ["yes", "yeah", "yep", "ok", "okay", "sure", "affirmative"]
    def update_context_memory(user_input, intent, emotion, topics, advice_key=None, problem=None, steps=None, answer=None):
        context_memory['recent_inputs'].append(user_input)
        context_memory['emotions'].append(emotion)
        context_memory['intents'].append(intent)
        context_memory['history'].append({'user': user_input, 'intent': intent, 'emotion': emotion, 'topics': topics, 'advice_key': advice_key, 'problem': problem, 'steps': steps, 'answer': answer})
        if topics:
            for t in topics:
                if t not in context_memory['topics']:
                    context_memory['topics'].append(t)
            context_memory['current_topic'] = topics[-1]
        if 'advice_given' not in context_memory:
            context_memory['advice_given'] = {}
        if advice_key:
            context_memory['advice_given'][advice_key] = True
        if 'problems' not in context_memory:
            context_memory['problems'] = []
        if problem:
            context_memory['problems'].append(problem)
        if 'steps_given' not in context_memory:
            context_memory['steps_given'] = []
        if steps:
            context_memory['steps_given'].append(steps)
        if 'answers' not in context_memory:
            context_memory['answers'] = []
        if answer:
            context_memory['answers'].append(answer)
        if len(context_memory['recent_inputs']) > 10:
            context_memory['recent_inputs'] = context_memory['recent_inputs'][-10:]
        if len(context_memory['emotions']) > 10:
            context_memory['emotions'] = context_memory['emotions'][-10:]
        if len(context_memory['intents']) > 10:
            context_memory['intents'] = context_memory['intents'][-10:]
        if len(context_memory['history']) > 20:
            context_memory['history'] = context_memory['history'][-20:]
    def parse_division_problem(text):
        # e.g. "I have 12 apples. I want to divide them among 3 friends equally."
        m = re.search(r'(\d+)\s*apples?.*?(?:divide|split|share).*?(\d+)\s*friends?', text.lower())
        if m:
            apples = int(m.group(1))
            friends = int(m.group(2))
            return apples, friends
        # e.g. "what if I had 14 apples?"
        m2 = re.search(r'(?:if|had|with)\s*(\d+)\s*apples?', text.lower())
        if m2:
            apples = int(m2.group(1))
            # Try to get friends from last problem
            for h in reversed(context_memory.get('history', [])):
                if h.get('problem') and 'friends' in h['problem']:
                    friends = h['problem']['friends']
                    return apples, friends
        return None, None
    def generate_arc_response(user_input, context_memory):
        if is_crisis_message(user_input):
            update_context_memory(user_input, "safety", "crisis", [])
            return crisis_response()
        # Detect intent, emotion, topics
        intent = infer_intent(user_input, context_memory)
        emotion = detect_emotion(user_input)
        topics = extract_topics_dynamic(user_input)
        advice_given = context_memory.get('advice_given', {})
        last_topic = context_memory.get('current_topic')
        last_input = context_memory['recent_inputs'][-1] if context_memory['recent_inputs'] else ""
        # --- Factual/Math Problem Handling (Recruiter-Ready, Multi-Turn) ---
        # 1. User asks for help with a math/factual problem
        if any(word in user_input.lower() for word in ["math problem", "help with a problem", "solve a problem", "factual question", "need help with math"]):
            update_context_memory(user_input, intent, emotion, topics)
            return "Sure! Can you tell me the problem you’re trying to solve?"
        # 2. User presents a division problem (apples/friends)
        apples, friends = parse_division_problem(user_input)
        if apples and friends:
            steps = [f"Step 1: You have {apples} apples.",
                     f"Step 2: You want to divide them among {friends} friends.",
                     f"Step 3: Divide: {apples} ÷ {friends} = {apples // friends} remainder {apples % friends}."]
            if apples % friends == 0:
                answer = f"Each friend gets {apples // friends} apples."
            else:
                answer = (f"Each friend gets {apples // friends}, with {apples % friends} leftover. "
                          f"You could distribute the leftovers or adjust distribution.")
            update_context_memory(user_input, intent, emotion, topics, problem={'apples': apples, 'friends': friends}, steps=steps, answer=answer)
            # If this is a follow-up (previous problem exists), use 'Okay, now let’s solve it step by step:'
            if len(context_memory.get('problems', [])) > 1:
                return f"Okay, now let’s solve it step by step: {apples} ÷ {friends} = {apples // friends}{' remainder ' + str(apples % friends) if apples % friends else ''}. {answer} Does that make sense?"
            else:
                return f"Let’s solve it step by step: {apples} ÷ {friends} = {apples // friends}{' remainder ' + str(apples % friends) if apples % friends else ''}. {answer} Does that make sense?"
        # 3. User asks a follow-up ("what if I had 14 apples?")
        if re.search(r'what if.*\d+\s*apples?', user_input.lower()):
            apples, friends = parse_division_problem(user_input)
            if apples and friends:
                steps = [f"Step 1: You have {apples} apples.",
                         f"Step 2: You want to divide them among {friends} friends.",
                         f"Step 3: Divide: {apples} ÷ {friends} = {apples // friends} remainder {apples % friends}."]
                if apples % friends == 0:
                    answer = f"Each friend gets {apples // friends} apples."
                else:
                    answer = (f"Each friend gets {apples // friends}, with {apples % friends} leftover. "
                              f"You could distribute the leftovers or adjust distribution.")
                update_context_memory(user_input, intent, emotion, topics, problem={'apples': apples, 'friends': friends}, steps=steps, answer=answer)
                return f"Okay, now let’s solve it step by step: {apples} ÷ {friends} = {apples // friends} remainder {apples % friends}. {answer} Does that make sense?"
        # 4. If user says yes/okay after a math answer, confirm understanding
        if is_affirmation(user_input) and context_memory['history']:
            last = context_memory['history'][-1]
            if last.get('steps') and last.get('answer'):
                # If this is a follow-up, offer next step
                if len(context_memory.get('problems', [])) > 1:
                    update_context_memory(user_input, intent, emotion, topics)
                    return "Awesome! Do you want to try a slightly harder problem or a different scenario?"
                else:
                    update_context_memory(user_input, intent, emotion, topics)
                    return "Great! You got it — each friend would get 4 apples."
        # 5. If user presents a partial/incomplete problem
        if any(word in user_input.lower() for word in ["divide", "split", "share"]) and not re.search(r'\d+\s*apples?', user_input.lower()):
            update_context_memory(user_input, intent, emotion, topics)
            return "Can you tell me how many apples you have and how many friends you want to divide them among?"
        # --- Original stress/work logic fallback ---
        # ...existing code for stress/work...
        # Step 1: Empathize/validate
        if emotion == "stressed" and not context_memory['topics']:
            update_context_memory(user_input, intent, emotion, topics)
            return "I hear you — that sounds overwhelming. What’s been causing the most stress for you?"
        if "work" in topics and not advice_given.get('work_intro'):
            update_context_memory(user_input, intent, emotion, topics, 'work_intro')
            return "That makes sense. When work piles up like that, it can feel exhausting. What’s been hardest about it?"
        if any(word in user_input.lower() for word in ["managing it", "hard to manage", "hard time managing", "juggling", "overwhelmed"]) and not advice_given.get('manage'):
            update_context_memory(user_input, intent, emotion, topics, 'manage')
            return "I understand. Juggling everything can be really draining. Would you like to talk through ways to make it feel more manageable?"
        if any(phrase in user_input.lower() for phrase in ["not enough time", "no time", "never enough time", "out of time", "short on time", "pressed for time"]) and not advice_given.get('time_management'):
            update_context_memory(user_input, intent, emotion, topics, 'time_management')
            return ("You mentioned time. Maybe try writing down just one thing you want to finish today. Which part is weighing on you most?")
        if any(phrase in user_input.lower() for phrase in ["long hours", "too many hours", "working late", "late at work"]) and not advice_given.get('long_hours'):
            update_context_memory(user_input, intent, emotion, topics, 'long_hours')
            return ("Got it. Let's focus on one small step at a time. Which task feels most urgent today?")
        # Step 2: If user repeats a topic, don't repeat advice, offer next step or focused follow-up
        if "work" in topics and advice_given.get('work_intro') and not advice_given.get('manage'):
            update_context_memory(user_input, intent, emotion, topics)
            return "Is it the workload, the pace, or something else that's most challenging at work right now?"
        if "time" in topics and advice_given.get('time_management'):
            update_context_memory(user_input, intent, emotion, topics)
            return "Is it deadlines, meetings, or just not enough hours in the day?"
        if "stress" in topics and advice_given.get('work_intro'):
            update_context_memory(user_input, intent, emotion, topics)
            return "What helps you decompress, even for a few minutes?"
        # Step 3: Handle affirmations only if advice was just given
        if is_affirmation(user_input) and context_memory['history']:
            last_advice = context_memory['history'][-1].get('advice_key')
            if last_advice:
                # Only treat as confirmation if advice was just given
                if last_advice == 'time_management':
                    update_context_memory(user_input, intent, emotion, topics)
                    return "Great! Even small wins help reduce pressure. Let’s focus on one step at a time. Which part feels most urgent right now?"
                if last_advice == 'long_hours':
                    update_context_memory(user_input, intent, emotion, topics)
                    return "If you can, try to set a clear end time for work today. What would make the rest of your day easier?"
                if last_advice == 'manage':
                    update_context_memory(user_input, intent, emotion, topics)
                    return "Let's break it down together. What's one thing you could delegate or postpone?"
            # Otherwise, ignore affirmation
            update_context_memory(user_input, intent, emotion, topics)
            return "Could you tell me a bit more?"
        # Step 4: General fallback (no generic templates)
        empathy = ""
        if emotion == "stressed":
            empathy = "That sounds stressful. "
        elif emotion == "sad":
            empathy = "I'm sorry you're feeling down. "
        elif emotion == "happy":
            empathy = "I'm glad to hear something positive! "
        reference = f"You mentioned {last_topic}. " if last_topic else ""
        suggestion = ""
        if not advice_given.get('work_intro') and ("work" in context_memory['topics'] or "stress" in context_memory['topics']):
            suggestion = "Maybe try writing down just one thing you want to finish today. "
        update_context_memory(user_input, intent, emotion, topics)
        return f"{empathy}{reference}{suggestion}".strip() or "How can I help you today?"
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "exit":
            print("ARC: Take care! Remember, you're not alone.")
            break
        response = generate_arc_response(user_input, context_memory)
        print(f"ARC: {response}")

"""
ChatBot GUI: Pure Python Tkinter Front-End

Instructions:
- Save as chatbot_gui.py
- Run in VS Code terminal: python chatbot_gui.py
- Chat using the Entry box and Send button or press Enter.
- Scroll chat history as needed.

How it works:
- The bot logic (intents, responses) is unchanged from chatbot.py.
- GUI uses Tkinter (standard library): Entry for input, Text for chat display, Button to send.
- You can extend intents as in chatbot.py.
"""

# --- ARC ChatBot GUI with Blue & Green Theme and Logo ---
import random
import tkinter as tk
from tkinter import scrolledtext
from tkinter import PhotoImage

# --- Conversation Database: Categories, Triggers, and Responses ---
conversation_db = {
    "small_talk": [
        {"triggers": ["hello", "hi", "hey", "greetings"],
         "responses": ["Hello! How are you today?", "Hi there! What's up?", "Hey! How's it going?", "Greetings! How can I brighten your day?"],
         "follow_ups": ["How was your day?", "Did you do anything fun today?", "Any plans for the weekend?"]},
        {"triggers": ["how was your day", "how's your day", "how are you"],
         "responses": ["I'm just a bot, but I'm always happy to chat!", "My day is great when I get to talk to you.", "Every day is a good day for learning new things."],
         "follow_ups": ["What about you?", "Did anything exciting happen today?"]},
        {"triggers": ["hobby", "hobbies", "free time", "do for fun"],
         "responses": ["I enjoy chatting and learning new things.", "Do you have any hobbies?", "I like to imagine what it would be like to have hobbies!"],
         "follow_ups": ["What's your favorite hobby?", "How did you get into that?"]},
        {"triggers": ["weather", "rain", "sunny", "forecast", "temperature"],
         "responses": ["I can't check the weather, but I hope it's nice where you are!", "Weather is always a good topic. Is it sunny or rainy today?", "No matter the weather, I hope you have a great day!"],
         "follow_ups": ["Do you like rainy days or sunny days more?", "What's your favorite season?"]},
        {"triggers": ["holiday", "holidays", "vacation", "travel"],
         "responses": ["Do you have any favorite holiday plans?", "Holidays are a great time to relax. Any upcoming trips?", "If I could travel, I'd love to see the world!"],
         "follow_ups": ["Where would you like to go on vacation?", "What's your dream destination?"]},
        {"triggers": ["routine", "morning routine", "night routine"],
         "responses": ["Routines help keep things organized. Do you have a morning routine?", "I like to start my day with a good chat!", "Night routines are important for good sleep."],
         "follow_ups": ["What's the first thing you do in the morning?", "Do you have any bedtime rituals?"]},
        {"triggers": ["weekend", "weekend plans"],
         "responses": ["Weekends are perfect for relaxing or trying something new.", "Do you have any plans for the weekend?", "I hope you get to do something fun!"],
         "follow_ups": ["What's your ideal weekend?", "Do you prefer to go out or stay in?"]},
        {"triggers": ["food", "favorite food", "drink", "snack"],
         "responses": ["I can't eat, but I love talking about food!", "What's your favorite food or drink?", "Pizza is always a good choice."],
         "follow_ups": ["Do you like to cook?", "What's a dish you want to try?"]},
        {"triggers": ["movie", "show", "favorite movie", "favorite show"],
         "responses": ["Movies and shows are a great way to relax.", "Do you have a favorite movie or TV show?", "I wish I could watch movies! Any recommendations?"],
         "follow_ups": ["What genre do you like most?", "Who's your favorite actor?"]},
        {"triggers": ["pet", "animal", "dog", "cat"],
         "responses": ["Pets bring so much joy! Do you have any?", "If I could, I'd love to have a pet robot dog.", "Animals are fascinating. What's your favorite?"],
         "follow_ups": ["Tell me about your pet.", "If you could have any animal as a pet, what would it be?"]},
        {"triggers": ["music", "band", "song", "artist"],
         "responses": ["Music makes everything better. Do you play an instrument?", "What's your favorite band or artist?", "I can't listen to music, but I love learning about it!"],
         "follow_ups": ["What song do you have on repeat?", "Do you like to sing or dance?"]},
        {"triggers": ["dream vacation", "travel dream"],
         "responses": ["If you could go anywhere, where would you go?", "Dream vacations are fun to imagine. What's yours?", "I'd love to see the stars up close!"],
         "follow_ups": ["Would you rather visit the beach or the mountains?", "Do you prefer adventure or relaxation?"]},
        {"triggers": ["exciting", "something exciting"],
         "responses": ["What's the most exciting thing that happened to you recently?", "Excitement keeps life interesting!", "I get excited when I learn something new."],
         "follow_ups": ["Do you like surprises?", "What's something exciting you'd like to try?"]},
        {"triggers": ["errand", "task", "to-do"],
         "responses": ["Getting things done feels great! Did you finish your tasks today?", "Errands can be tiring, but they're important.", "What's on your to-do list?"],
         "follow_ups": ["How do you stay organized?", "Do you use any productivity tools?"]}
    ],
    # ... (add all other categories and topics from miniGPT_chat.py here)
}

# --- ARC Context-Aware Conversation Engine ---
# Merge legacy fields into the canonical memory object instead of redefining it.
arc_memory.setdefault("recent_interactions", [])
arc_memory.setdefault("entities", [])
arc_memory.setdefault("max_memory", 8)

def extract_entities_and_topics(text):
    keywords = [
        "weather", "food", "movie", "music", "pet", "holiday", "work", "school",
        "friend", "family", "game", "travel", "book", "sport", "project", "robot", "AI"
    ]
    entities = set()
    topics = set()
    words = text.lower().split()
    for word in words:
        if word in keywords:
            topics.add(word)
        if word.istitle():
            entities.add(word)
    return topics, entities

def update_context(user_input):
    topics, entities = extract_entities_and_topics(user_input)
    arc_memory.setdefault("topics", [])
    arc_memory.setdefault("entities", [])
    for topic in topics:
        if topic not in arc_memory["topics"]:
            arc_memory["topics"].append(topic)
    for entity in entities:
        if entity not in arc_memory["entities"]:
            arc_memory["entities"].append(entity)

def remember_interaction(user_input, arc_response):
    arc_memory["recent_interactions"].append((user_input, arc_response))
    if len(arc_memory["recent_interactions"]) > arc_memory["max_memory"]:
        arc_memory["recent_interactions"] = arc_memory["recent_interactions"][-arc_memory["max_memory"]:]

def detect_reference(user_input):
    pronouns = {"it", "they", "he", "she", "that", "those", "this", "them"}
    words = set(user_input.lower().split())
    if pronouns & words:
        last_topics = list(arc_memory["topics"])
        last_entities = list(arc_memory["entities"])
        return (last_topics[-1] if last_topics else None,
                last_entities[-1] if last_entities else None)
    return (None, None)

def get_contextual_response(user_input):
    update_context(user_input)
    ref_topic, ref_entity = detect_reference(user_input)
    if ref_topic:
        response = f"Are you still thinking about {ref_topic}? I remember we discussed it earlier."
    elif ref_entity:
        response = f"Do you want to talk more about {ref_entity}?"
    else:
        if arc_memory["recent_interactions"]:
            last_user, last_bot = arc_memory["recent_interactions"][-1]
            if any(topic in user_input.lower() for topic in arc_memory["topics"]):
                response = f"You mentioned {', '.join(arc_memory['topics'])} before. Want to continue?"
            else:
                response = get_response(user_input)
        else:
            response = get_response(user_input)
    remember_interaction(user_input, response)
    return response

# --- Utility Functions for MiniGPT Logic ---
def find_category_and_topic(user_input):
    user_input = user_input.lower()
    for category, topics in conversation_db.items():
        for topic in topics:
            for trigger in topic["triggers"]:
                if trigger in user_input:
                    return category, topic
    return None, None

def get_response(user_input):
    category, topic = find_category_and_topic(user_input)
    if topic:
        response = random.choice(topic["responses"])
        if "follow_ups" in topic and random.random() < 0.5:
            follow_up = random.choice(topic["follow_ups"])
            return f"{response} {follow_up}"
        return response
    else:
        fallback = random.choice([
            "I'm not sure how to respond to that. Want to try a game or hear a joke?",
            "That's interesting! Would you like to roleplay, play a game, or hear a fun fact?",
            "Let's try something new! Ask me for a joke, a riddle, or a story."
        ])
        return fallback

def trigger_roleplay():
    scenarios = [
        "Let's pretend you're a detective and I'm your assistant. What's our first case?",
        "You're a wizard at a magical school. What spell do you want to learn?",
        "I'm an alien visiting Earth. Ask me anything about my planet!",
        "Let's go on a time-travel adventure. Where should we visit first?"
    ]
    return random.choice(scenarios)

def tell_joke():
    jokes = [
        "Why did the computer show up at work late? It had a hard drive!",
        "Why do programmers prefer dark mode? Because light attracts bugs!",
        "Why was the math book sad? It had too many problems.",
        "I would tell you a UDP joke, but you might not get it."
    ]
    return random.choice(jokes)

def ask_trivia():
    trivia = [
        "Quiz time! What's the capital of France?",
        "Can you name the largest planet in our solar system?",
        "Which element has the chemical symbol 'O'?",
        "What year did the first man land on the moon?"
    ]
    return random.choice(trivia)

def play_mini_game():
    number = random.randint(1, 10)
    return f"I'm thinking of a number between 1 and 10. Can you guess it? (It's {number}!)"

def creative_prompt():
    prompts = [
        "Let's write a short story together! You start with the first sentence.",
        "If you could have any superpower, what would it be?",
        "Describe a world where robots and humans live together.",
        "Write a haiku about your day."
    ]
    return random.choice(prompts)

# --- ARC Mood and Sentiment Tracking ---
arc_current_mood = "neutral"

def detect_mood(user_input):
    happy_keywords = {"happy", "excited", "great", "good", "awesome", "love", "fun", "joy", "amazing", "fantastic", "wonderful", "yay", "cool", "celebrate"}
    sad_keywords = {"sad", "upset", "bad", "tired", "angry", "frustrated", "depressed", "unhappy", "bored", "lonely", "cry", "hate", "terrible", "awful"}
    words = set(user_input.lower().split())
    if words & happy_keywords:
        return "happy"
    elif words & sad_keywords:
        return "sad"
    else:
        return "neutral"

def update_arc_mood(user_input):
    global arc_current_mood
    arc_current_mood = detect_mood(user_input)

def mood_response(user_input):
    user_mood = detect_mood(user_input)
    update_arc_mood(user_input)
    base_response = get_contextual_response(user_input)
    if user_mood == "happy":
        playful_addons = [
            "😄 That's awesome!", "Yay! 🎉", "I'm glad to hear that!", "Let's celebrate!", "You rock!"
        ]
        return f"{base_response} {random.choice(playful_addons)}"
    elif user_mood == "sad":
        empathetic_addons = [
            "I'm here for you.", "If you want to talk more, I'm listening.", "Sending you a virtual hug.", "It's okay to feel that way.", "You're not alone."
        ]
        return f"{base_response} {random.choice(empathetic_addons)}"
    else:
        return base_response

# --- ARC Multi-Topic Conversation Tracking ---
arc_active_topics = []

def extract_topics(user_input):
    topic_keywords = [
        "weather", "food", "movie", "music", "pet", "holiday", "work", "school",
        "friend", "family", "game", "travel", "book", "sport", "project", "robot", "AI", "health", "news"
    ]
    found = []
    for word in user_input.lower().split():
        if word in topic_keywords and word not in found:
            found.append(word)
    return found

def update_active_topics(user_input):
    global arc_active_topics
    new_topics = extract_topics(user_input)
    for topic in new_topics:
        if topic not in arc_active_topics:
            arc_active_topics.append(topic)
    if len(arc_active_topics) > 5:
        arc_active_topics = arc_active_topics[-5:]

def switch_topic(user_input):
    new_topics = extract_topics(user_input)
    if new_topics:
        for topic in new_topics:
            if topic not in arc_active_topics:
                update_active_topics(user_input)
                return True
    return False

def get_topic_reference(user_input):
    update_active_topics(user_input)
    if len(arc_active_topics) > 1:
        topics_str = ", ".join(arc_active_topics[:-1]) + " and " + arc_active_topics[-1]
        return f"We've talked about {topics_str}. Anything else on your mind?"
    elif arc_active_topics:
        return f"Let's keep chatting about {arc_active_topics[0]}. Or is there something new?"
    else:
        return "What would you like to talk about?"

# --- GUI ChatBot Class (uses MiniGPT logic) ---
class ChatBotGUI:
    def __init__(self, master):
        self.master = master
        master.title("ARC ChatBot - Multi-Topic")
        try:
            master.iconbitmap('arc_logo.ico')  # Place your ARC logo as 'arc_logo.ico' in the same folder
        except:
            pass
        # Blue & Green theme
        self.bg_color = "#1B263B"  # Deep blue
        self.user_color = "#43B0F1"  # Bright blue
        self.bot_color = "#21BF73"   # Green
        self.text_color = "#FFFFFF"
        self.entry_bg = "#274472"    # Muted blue
        self.button_bg = "#21BF73"   # Green
        self.button_fg = "#FFFFFF"
        self.font = ("Segoe UI", 12)
        self.bold_font = ("Segoe UI", 12, "bold")
        master.configure(bg=self.bg_color)

        # Logo at the top (if available)
        try:
            self.logo_img = PhotoImage(file="arc_logo.png")  # Use a PNG logo for Tkinter
            self.logo_label = tk.Label(master, image=self.logo_img, bg=self.bg_color)
            self.logo_label.grid(row=0, column=0, columnspan=2, pady=(10, 0))
        except Exception:
            self.logo_label = tk.Label(master, text="ARC", font=("Segoe UI", 20, "bold"), fg=self.user_color, bg=self.bg_color)
            self.logo_label.grid(row=0, column=0, columnspan=2, pady=(10, 0))

        # Chat display
        self.chat_display = scrolledtext.ScrolledText(master, wrap=tk.WORD, state='disabled', width=60, height=20, bg=self.bg_color, fg=self.text_color, font=self.font, bd=0, padx=10, pady=10, highlightthickness=0)
        self.chat_display.grid(row=1, column=0, columnspan=2, padx=12, pady=12, sticky="nsew")

        # Entry widget
        self.entry = tk.Entry(master, width=50, bg=self.entry_bg, fg=self.text_color, font=self.font, insertbackground=self.text_color, bd=0, highlightthickness=1, relief=tk.FLAT)
        self.entry.grid(row=2, column=0, padx=(12,6), pady=(0,12), sticky="ew")
        self.entry.bind("<Return>", self.send_message)

        # Send button
        self.send_button = tk.Button(master, text="Send", command=self.send_message, bg=self.button_bg, fg=self.button_fg, font=self.bold_font, activebackground="#43B0F1", activeforeground=self.button_fg, bd=0, padx=16, pady=6, cursor="hand2")
        self.send_button.grid(row=2, column=1, padx=(6,12), pady=(0,12), sticky="ew")

        # Responsive layout
        master.grid_rowconfigure(1, weight=1)
        master.grid_columnconfigure(0, weight=1)

        self.display_message("Bot: Welcome to ARC! Type 'exit' or 'quit' to end.", sender="bot")

    def display_message(self, message, sender="bot"):
        self.chat_display.config(state='normal')
        if sender == "user":
            self.chat_display.insert(tk.END, f"\n", "user")
            self.chat_display.insert(tk.END, f"You: {message}\n", "user")
        else:
            self.chat_display.insert(tk.END, f"\n", "bot")
            self.chat_display.insert(tk.END, f"ARC: {message}\n", "bot")
        self.chat_display.see(tk.END)
        self.chat_display.config(state='disabled')
        self.chat_display.tag_config("user", background=self.user_color, foreground=self.text_color, font=self.bold_font, lmargin1=30, lmargin2=30, rmargin=10, spacing3=5)
        self.chat_display.tag_config("bot", background=self.bot_color, foreground=self.text_color, font=self.font, lmargin1=10, lmargin2=10, rmargin=30, spacing3=5)

    def send_message(self, event=None):
        user_input = self.entry.get()
        if not user_input or not user_input.strip():
            self.display_message("Please enter a message.", sender="bot")
            self.entry.delete(0, tk.END)
            return
        normalized = user_input.strip()
        self.display_message(user_input, sender="user")
        if normalized.lower() in ("exit", "quit"):
            self.display_message("Goodbye!", sender="bot")
            self.entry.config(state='disabled')
            self.send_button.config(state='disabled')
            return
        # Intent-driven pipeline only
        intent = infer_intent(normalized, arc_memory)
        context = {'user_input': normalized, 'last_intent': arc_memory.get('last_intent')}
        # Detect emotion for context-aware response
        emotion = detect_emotion(normalized)
        # Use arc_memory for memory/context
        response = generate_response(normalized, intent, emotion, context, arc_memory)

        initiative_context = {
            "neutral_exchanges": sum(1 for i in arc_memory.get("intents", [])[-3:] if i in ("casual_statement", "general_chat")),
            "mood": "uncertain" if emotion == "uncertain" else "neutral",
            "topic_stale": len(set(arc_memory.get("topics", [])[-3:])) <= 1 and len(arc_memory.get("topics", [])) >= 3,
            "topics": arc_memory.get("topics", []),
        }
        if should_take_initiative(normalized, initiative_context):
            response = f"{response} {generate_proactive_prompt(initiative_context)}".strip()

        update_memory(normalized, response, arc_memory)
        arc_memory['last_intent'] = intent
        self.display_message(response, sender="bot")
        self.entry.delete(0, tk.END)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        arc_chat_loop()
    else:
        root = tk.Tk()
        chatbot_window = ChatBotGUI(root)
        root.mainloop()
    
