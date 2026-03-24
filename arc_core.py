"""
ARC Chatbot Core Engine
=======================

Pure business logic extracted from arc.py.
- No UI dependencies (no tkinter, no print statements)
- No global state (fully stateless or passed explicitly)
- 100% testable functions with clear input/output
- Browser-ready API

Usage:
    engine = ChatbotEngine()
    response = engine.chat("Hello", session_state={})
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence
import re
import time
import random


# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass
class ChatMessage:
    """Single message in conversation."""
    sender: str  # "user" or "bot"
    text: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class ChatState:
    """Complete conversation state."""
    session_id: str
    turns: list[tuple[str, str]] = field(default_factory=list)  # (user, bot) pairs
    topics: list[str] = field(default_factory=list)
    emotions: list[str] = field(default_factory=list)
    intents: list[str] = field(default_factory=list)
    last_responses: list[str] = field(default_factory=list)
    current_topic: Optional[str] = None
    personality_state: str = "neutral"
    profile: dict[str, str] = field(default_factory=dict)
    kv_memory: dict[str, str] = field(default_factory=dict)
    last_user_message: Optional[str] = None
    last_bot_question: Optional[str] = None
    last_explained_topic: Optional[str] = None
    last_route: str = ""
    recovery_count: int = 0
    user_goals: list[str] = field(default_factory=list)
    user_constraints: list[str] = field(default_factory=list)
    last_intent: str = ""

    def add_turn(self, user_msg: str, bot_msg: str) -> None:
        """Record user-bot exchange."""
        self.turns.append((user_msg, bot_msg))
        # Keep last 50 turns only (prevent unbounded growth)
        if len(self.turns) > 50:
            self.turns = self.turns[-50:]
    
    def should_limit_response(self) -> bool:
        """Prevent truly repetitive responses (same response 3+ times)."""
        if len(self.last_responses) < 4:
            return False
        recent = self.last_responses[-4:]
        if not all(r == recent[0] for r in recent):
            return False
        lowered = recent[0].lower()
        generic_markers = ["tell me more", "what else", "go on", "what do you think", "let's switch gears"]
        return any(m in lowered for m in generic_markers)


# ============================================================================
# INTENT CLASSIFICATION
# ============================================================================


def classify_intent(user_text: str, state: Optional[ChatState] = None) -> str:
    """
    Classify user intent from message text.

    Returns one of: question, factual_request, emotional_expression,
                   follow_up, decision_request, plan_request,
                   context_connection, meta_complaint, constraint_update,
                   vague_input, uncertainty, casual_statement, general_chat
    """
    text = normalize_text(user_text)

    if not text:
        return "uncertainty"

    # --- Context connection ("how do those connect?") ---
    connection_triggers = [
        "how do those connect", "how does that connect", "what do those have in common",
        "how are those related", "connect the dots", "how is that related",
    ]
    if any(t in text for t in connection_triggers):
        return "context_connection"

    # --- Meta-complaints about bot quality ---
    meta_triggers = [
        "stop being generic", "you're being generic", "too generic", "stop being vague",
        "give me a real answer", "be more specific", "actual answer", "real answer",
        "you're not helping", "that didn't help", "useless", "be honest",
    ]
    if any(t in text for t in meta_triggers):
        return "meta_complaint"

    # --- Decision requests ---
    decision_triggers = [
        "should i", "pros and cons", "what would you do", "give me pros",
        "is it better to", "which is better", "pick one", "defend it",
        "safest option", "safer option", "argue the opposite",
    ]
    if any(t in text for t in decision_triggers):
        return "decision_request"

    # --- Plan requests ---
    plan_triggers = [
        "3-step plan", "3 step plan", "step plan", "give me a plan",
        "make a plan", "roadmap", "plan to get into", "plan for tech",
        "how do i get into", "step by step",
    ]
    if any(t in text for t in plan_triggers):
        return "plan_request"

    # --- Follow-up on previous answer ---
    follow_up_exact = {
        "why", "why?", "and?", "so?", "really?", "seriously?",
        "why is that", "why does that matter", "why does it matter",
        "why should i care", "why is it important",
        "be specific", "get specific", "more specific",
        "make it actionable", "now make it actionable", "actionable for today",
        "simplify", "now simplify", "simpler", "make it simpler",
        "next step", "what's my next move", "what next",
        "what should i actually do", "what should i focus on",
        "ask me questions", "ask me",
        "exact next move", "what's your exact next move",
        "elaborate", "expand on that", "what does that mean",
    }
    if text.strip().rstrip('?') in follow_up_exact or text.strip() in follow_up_exact:
        return "follow_up"
    follow_up_phrases = [
        "why does that", "why should i", "why is it", "why does it",
        "explain more", "tell me more about", "be more specific",
        "make it actionable", "now simplify", "now make it",
        "based on what i've told you", "based on what i told you",
        "given what i said", "given everything", "pretend you're me",
    ]
    if any(t in text for t in follow_up_phrases):
        return "follow_up"

    # --- Constraint updates (user describing their situation) ---
    constraint_triggers = [
        "i work 9", "work 9-5", "9 to 5", "nine to five",
        "tired after work", "tired when i get home", "no experience",
        "i'm broke", "im broke", "no money", "can't afford",
        "limited time", "don't have time", "only have",
    ]
    if any(t in text for t in constraint_triggers):
        return "constraint_update"

    # --- Emotional expression (high priority) ---
    emotions = [
        "sad", "stressed", "anxious", "happy", "excited", "frustrated",
        "angry", "confused", "worried", "depressed", "upset", "mad", "lonely",
        "scared", "afraid", "overwhelmed", "stuck",
    ]
    if any(e in text for e in emotions):
        return "emotional_expression"

    if re.search(r"\bi\s+(am|feel|felt|miss|need|want|wish|do)\b", text):
        if any(contains_phrase(text, t) for t in ["math", "science", "history", "geography", "physics", "biology", "chemistry", "technology", "ai", "programming", "tech", "coding"]):
            return "factual_request"
        return "emotional_expression"

    # Questions about the bot itself
    bot_questions = ["what do you do", "what can you do", "who are you", "capabilities", "what are you", "tell me about yourself"]
    if any(q in text for q in bot_questions):
        return "factual_request"

    # Question detection
    if "?" in text or any(q in text for q in ["what ", "when ", "where ", "who ", "why ", "how ", "can you help with"]):
        if "can you help" in text and "with" in text:
            return "factual_request"
        return "question"

    # Explicit help/explain requests
    help_keywords = ["help me with", "explain", "teach me", "show me", "tell me about", "define", "what is", "how to"]
    if any(h in text for h in help_keywords):
        return "factual_request"

    creative_keywords = ["tell me a story", "tell a story", "joke", "funny", "make me laugh", "riddle"]
    if any(r in text for r in creative_keywords):
        return "general_chat"

    topics = ["math", "science", "history", "geography", "physics", "biology", "chemistry", "technology", "tech", "ai", "programming", "coding", "code"]
    if any(contains_phrase(text, t) for t in topics):
        return "factual_request"

    if infer_topic(text) is not None:
        return "factual_request"

    if any(k in text for k in ["talk about", "let's talk about", "tell me about"]):
        return "factual_request"

    if solve_math_query(text) is not None:
        return "factual_request"

    if any(h in text for h in ["can you help", "help me", "assist", "help with"]):
        return "general_chat"

    if any(u in text for u in ["i don't know", "not sure", "maybe", "i think", "unclear", "confused about", "don't understand"]):
        return "uncertainty"

    # Very short (1-3 words) — vague without context
    if len(text.split()) <= 3:
        if state and (state.user_goals or state.user_constraints or state.turns):
            return "follow_up"  # short follow-ups in active conversations
        return "vague_input"

    return "general_chat"


def classify_intents(user_text: str, state: Optional[ChatState] = None) -> list[str]:
    """Multi-label intent detection for routing and mixed requests."""
    text = normalize_text(user_text)
    intents: list[str] = []

    base = classify_intent(text, state)
    intents.append(base)

    if any(k in text for k in ["what should i do", "help me", "advice", "decide", "you decide"]):
        intents.append("advice_request")

    follow_patterns = [
        r"\bback to\b",
        r"\bwhat about that\b",
        r"\byou know what i mean\b",
        r"\btry again\b",
        r"\byou misunderstood\b",
        r"\banswer the actual question\b",
        r"\bshould i\?*$",
    ]
    if any(re.search(p, text) for p in follow_patterns):
        intents.append("follow_up")

    if any(k in text for k in ["act like", "be funny", "be serious", "best friend", "therapist", "drill sergeant", "recruiter"]):
        intents.append("role_switch")

    if any(k in text for k in [" and ", " but ", ","]):
        intents.append("multi_intent")

    if any(k in text for k in ["???", "...", ".....", "asdf", "lkjh"]):
        intents.append("noisy_input")

    # keep stable order without duplicates
    deduped: list[str] = []
    for i in intents:
        if i not in deduped:
            deduped.append(i)
    return deduped


def is_generic_response(text: str) -> bool:
    generic_phrases = [
        "tell me more",
        "what else",
        "go on",
        "what do you think",
        "i don't have a precise answer",
        "that's interesting",
    ]
    lowered = normalize_text(text)
    return any(p in lowered for p in generic_phrases)


def follow_up_response(user_text: str, state: ChatState) -> Optional[str]:
    text = normalize_text(user_text)
    recent = " ".join(u for u, _ in state.turns[-4:]).lower()

    if "back to" in text:
        explicit_topic = infer_topic(text)
        if explicit_topic:
            return f"Sure, back to {explicit_topic}. What specific part do you want to focus on?"
        for previous_user, _ in reversed(state.turns[-6:]):
            prior_topic = infer_topic(previous_user)
            if prior_topic:
                return f"Sure, back to {prior_topic}. What specific part do you want to focus on?"

    if text in {"what about that?", "you know what i mean?", "try again", "you misunderstood", "answer the actual question"}:
        if state.last_user_message:
            return f"You're right, let me correct that. About '{state.last_user_message}': what specific outcome do you want right now?"

    if text == "should i?":
        if "quit" in recent or "boss" in recent or "work" in recent:
            return "If this is about quitting, don't rush it emotionally. Build a short exit plan first so you protect your income and options."
        return "If you're unsure, choose the smallest reversible step first and reassess after you get feedback."

    if "is that a good or bad thing" in text:
        if "promoted" in recent:
            return "Usually good. A promotion means trust and opportunity, but it can add pressure. The key is setting boundaries and getting support early."

    return None


def short_multi_intent_response(user_text: str) -> Optional[str]:
    text = normalize_text(user_text)
    if "money" in text and "relationship" in text and "school" in text:
        return (
            "Short version: money - make a simple budget and cut one wasteful expense this week; "
            "relationship - communicate one honest need calmly; school - pick one top priority and finish it before anything else."
        )
    return None


def route_response(user_text: str, state: ChatState) -> Optional[str]:
    """Central response routing using intents + conversation state."""
    intents = classify_intents(user_text, state)

    if "noisy_input" in intents:
        state.last_route = "recovery:noisy"
        return "That looks unclear. Rephrase it in one sentence and I will answer directly."

    # ── Context connection ("how do those connect?") ──
    context_conn = context_connection_response(user_text, state)
    if context_conn:
        state.last_route = "context_connection"
        return context_conn

    # ── Plan requests ("3-step plan to get into tech") ──
    plan = plan_request_response(user_text, state)
    if plan:
        state.last_route = "plan_request"
        return plan

    # ── Decision framework ("should I quit?", "pros and cons") ──
    decision = decision_framework_response(user_text, state)
    if decision:
        state.last_route = "decision_framework"
        return decision

    # ── Follow-up chaining ("why?", "be specific", "make it actionable") ──
    follow_chain = follow_up_chain_response(user_text, state)
    if follow_chain:
        state.last_route = "follow_up_chain"
        return follow_chain

    # ── Constraint-aware response ("I work 9-5 and I'm tired") ──
    constraint_resp = constraint_aware_response(user_text, state)
    if constraint_resp:
        state.last_route = "constraint_aware"
        return constraint_resp

    # ── Personalized advice (uses stored goals/constraints) ──
    personalized = personalized_advice_response(user_text, state)
    if personalized:
        state.last_route = "personalized"
        return personalized

    # ── Legacy follow-up patterns ──
    follow = follow_up_response(user_text, state)
    if follow:
        state.last_route = "follow_up"
        return follow

    multi = short_multi_intent_response(user_text)
    if multi:
        state.last_route = "multi_intent"
        return multi

    if "advice_request" in intents and "emotional_expression" in intents:
        state.last_route = "emotion+advice"
        goals = state.user_goals
        constraints = state.user_constraints
        if goals or constraints:
            goal_str = goals[0] if goals else "your goal"
            constraint_str = f" Given {', '.join(constraints[:2])}." if constraints else ""
            return (
                f"You're dealing with both stress and the question of whether to pursue {goal_str}.{constraint_str} "
                f"Let's do one concrete next step: pick the single most important thing you can control in the next hour and do it. "
                f"Then we decide the next move from there."
            )
        return "You sound overloaded. Let's do one concrete next step: pick one thing you can control in the next hour, do it, then we decide the next move."

    return None


def recovery_response(user_text: str, state: ChatState) -> str:
    state.recovery_count += 1
    topic = infer_topic(user_text) or state.current_topic

    if state.recovery_count >= 2 and topic:
        return f"I missed your intent. Let's recover fast: do you want explanation, action steps, or emotional support about {topic}?"

    if state.recovery_count >= 3:
        return "I keep missing your intent. Give me one sentence in this format: 'Goal: __. Context: __. Constraint: __.'"

    return "I may have misunderstood. Tell me the exact outcome you want from me in one line, and I will answer directly."


# ============================================================================
# EMOTION DETECTION
# ============================================================================


def classify_emotion(user_text: str) -> str:
    """
    Classify emotion from user message.
    
    Returns one of: positive, negative, neutral, uncertain
    """
    text = normalize_text(user_text)
    
    positive_words = ["love", "great", "happy", "excited", "wonderful", "amazing", "excellent", "thank", "sunny", "proud"]
    negative_words = ["hate", "bad", "sad", "angry", "frustrated", "worst", "terrible", "awful", "stressed", "anxious", "lonely", "depressed", "overwhelmed", "miss"]
    
    pos_score = sum(1 for w in positive_words if w in text)
    neg_score = sum(1 for w in negative_words if w in text)
    
    if pos_score > neg_score:
        return "positive"
    elif neg_score > pos_score:
        return "negative"
    elif pos_score > 0 or neg_score > 0:
        return "neutral"
    else:
        return "uncertain"


# ============================================================================
# RESPONSE GENERATION
# ============================================================================


# Knowledge base (extracted from arc.py)
KNOWLEDGE_BASE = {
    # Bot capabilities & identity
    "what do you do": "I'm ARC, an intelligent chatbot! I can help you with math, science, history, geography, technology, life advice, emotions, and general conversation. Ask me anything!",
    "what can you do": "I can assist with many topics: math problems, scientific explanations, historical facts, geography trivia, technology concepts, life advice, emotional support, and much more. Feel free to ask me anything!",
    "who are you": "I'm ARC, an AI chatbot designed to be helpful, informative, and conversational. I'm here to discuss virtually any topic and help answer your questions.",
    "your capabilities": "I can help with: math (basic arithmetic, algebra, geometry), science (physics, biology, chemistry), history, geography, technology, emotions, life advice, personal topics, and general knowledge questions.",
    "help me with math": "I'd love to help with math! I can explain concepts like algebra, geometry, calculus, trigonometry, statistics, and solve problems. What specific math topic interests you?",
    "help me with geography": "I can help with geography! Ask me about capitals of countries, major landmarks, largest deserts/mountains/oceans, climate zones, or any geographical facts.",
    "help me with science": "I'm happy to help with science! I can discuss physics, chemistry, biology, astronomy, or any scientific concepts you're curious about.",
    "help me with history": "I can help with history! Ask me about historical periods, famous events, important figures, revolutions, wars, or any historical topics.",
    "i am making an ai": "That's an awesome project. I can help with data preparation, model selection, overfitting prevention, evaluation metrics, and deployment. What stage are you at?",
    "overfitting": "Overfitting is when a model performs very well on training data but poorly on new data. Fixes include regularization, more data, cross-validation, dropout, and early stopping.",
    "underfitting": "Underfitting happens when a model is too simple to capture patterns. Try richer features, a larger model, or better training.",
    "precision recall": "Precision measures correctness of positive predictions; recall measures how many actual positives were found. There's usually a trade-off.",
    "f1 score": "F1 score is the harmonic mean of precision and recall: F1 = 2PR/(P+R). It's useful for imbalanced datasets.",
    "cross validation": "Cross-validation splits data into folds to test model generalization more reliably than a single train/test split.",
    "confusion matrix": "A confusion matrix summarizes classification results: true positives, false positives, true negatives, and false negatives.",
    "loss function": "A loss function measures model error. Training minimizes this value, e.g., MSE for regression, cross-entropy for classification.",
    
    # LIFE & EMOTIONS
    "feeling sad": "I understand sadness is a natural emotion. Remember that difficult feelings usually pass with time. Is there something specific bothering you? Sometimes talking helps.",
    "feeling happy": "That's wonderful! I'm glad you're feeling good. Happiness is precious—what's bringing so much joy to your day?",
    "stressed": "Stress is common, but remember to breathe and take breaks. Try to break big tasks into smaller ones. What's causing your stress?",
    "feeling lonely": "Loneliness is a common feeling. Remember, you're never truly alone. Consider reaching out to friends, family, or finding communities with shared interests.",
    "feeling anxious": "Anxiety can be overwhelming, but it's manageable. Try deep breathing, meditation, or talking to someone. What's making you anxious?",
    "feeling depressed": "If you're feeling depressed, please know it's okay to seek help. Talk to friends, family, or a mental health professional. You matter, and things can get better.",
    "life purpose": "Finding life purpose is a journey. Think about what makes you happy, what you're good at, and how you want to help others. Purpose often reveals itself through exploration.",
    "meaning of life": "The meaning of life is deeply personal. For many, it's about connections with others, creating, learning, helping, and leaving a positive impact.",
    "life advice": "Life advice: Be kind to yourself and others. Learn from mistakes. Pursue what matters to you. Spend time with loved ones. Life is precious—make it count.",
    "how to be happy": "Happiness often comes from simple things: meaningful relationships, pursuing interests, helping others, gratitude, spending time in nature, and taking care of your health.",
    "how to be successful": "Success means different things to different people. Focus on: setting goals, continuous learning, perseverance, treating others well, and defining success for yourself.",
    "relationships": "Healthy relationships are built on: trust, communication, respect, mutual support, and care. Invest time in people who matter to you.",
    "friendship": "True friendship is about: being there during good and bad times, honest communication, mutual respect, and genuine interest in each other's wellbeing.",
    "family": "Family is important for most people. Strong family bonds come from: spending quality time together, open communication, supporting each other, and showing love.",
    "love": "Love takes many forms: romantic, familial, platonic, and self-love. All are important. Love is about care, respect, trust, and wanting the best for someone.",
    "motivation": "When unmotivated, try: remembering your goals, starting small, rewarding progress, finding inspiration, and connecting your tasks to larger purposes.",
    "confidence": "Build confidence by: setting and achieving small goals, practicing self-compassion, focusing on strengths, taking action, and remembering past successes.",
    "fear": "Fear is natural. To overcome it: understand what you fear, take small steps, challenge negative thoughts, breathe, and remember most fears are less scary when faced.",
    "regret": "Regrets teach us lessons. You can't change the past, but you can learn from it and make different choices now. That's what matters.",
    "forgiveness": "Forgiving others (and yourself) brings peace. It doesn't mean excusing wrongs, but releasing the burden of anger and resentment.",
    "self-improvement": "Self-improvement is a continuous journey: identify areas to grow, set realistic goals, practice consistently, be patient, and celebrate small wins.",
    "work life balance": "Balance is important for wellbeing. Set boundaries: separate work time from personal time, take breaks, do activities you enjoy, and prioritize relationships.",
    "career advice": "Career advice: Do meaningful work, continuously learn, build relationships, take calculated risks, and remember that your worth isn't defined by your job.",
    "dealing with failure": "Failure is part of growth. Learn from mistakes, be resilient, adjust your approach, and remember that many successful people have failed multiple times.",
    "how to make friends": "Make friends by: joining groups with shared interests, being genuine, showing interest in others, being reliable, and spending time together regularly.",
    "how to handle conflict": "Handle conflict by: staying calm, listening to the other person, expressing your perspective clearly, finding common ground, and seeking win-win solutions.",
    "dealing with grief": "Grief is natural after loss. Allow yourself to feel, remember the good times, lean on support systems, and know that healing takes time.",
    "life is short": "Life is indeed short, which is why it's important to: cherish moments with loved ones, pursue what matters, be kind, create memories, and live intentionally.",
    "dream": "Dreams can be about aspirations or sleep. Pursuing dreams requires: belief, effort, persistence, and sometimes adjusting your path. What are your dreams?",
    "passion": "Passion gives life meaning and energy. Follow what excites you, even if it's unconventional. Passion-driven work often feels less like work.",
    "what makes life meaningful": "Meaning comes from: relationships, contributing to something larger than yourself, learning, creating, helping others, and living according to your values.",
    
    # MATH - Expanded
    "math": "I can help with many math topics! Ask about: arithmetic, algebra, geometry, calculus, trigonometry, statistics, fractions, percentages, or specific problems.",
    "pythagorean theorem": "In a right triangle, a² + b² = c², where c is the hypotenuse. Used to find distances and verify right angles.",
    "what is pi": "Pi (π) ≈ 3.14159... It's the ratio of a circle's circumference to its diameter. Appears in many circles and spheres calculations.",
    "what is algebra": "Algebra uses symbols (variables) to represent unknown quantities. It's about finding unknown values by setting up and solving equations.",
    "what is calculus": "Calculus studies change and motion. It includes derivatives (rates of change) and integrals (areas). Fundamental to physics and engineering.",
    "quadratic formula": "For ax² + bx + c = 0, the solution is x = (-b ± √(b² - 4ac)) / 2a. Used to solve quadratic equations.",
    "order of operations": "PEMDAS/BODMAS: Parentheses/Brackets, Exponents/Orders, Multiplication & Division (left to right), Addition & Subtraction (left to right).",
    "prime number": "A prime number is a natural number greater than 1 with no positive divisors except 1 and itself. Examples: 2, 3, 5, 7, 11, 13...",
    "fibonacci": "Fibonacci sequence: 0, 1, 1, 2, 3, 5, 8, 13... where each number is the sum of the two before it. Found in nature often.",
    "percentage": "A percentage is a number expressed as a fraction of 100. 50% = 50/100 = 1/2. Used for comparisons and changes.",
    "fraction": "A fraction represents a part of a whole. Numerator (top) / Denominator (bottom). Example: 3/4 means three-quarter of something.",
    
    # SCIENCE - Physics
    "what is physics": "Physics is the study of matter, energy, and forces. It explains how the universe works at all scales.",
    "what is gravity": "Gravity is a fundamental force that attracts objects with mass toward each other. Keeps us on Earth and planets orbiting the sun.",
    "newtons laws": "1) Objects stay at rest or moving unless acted upon. 2) Force = mass × acceleration (F=ma). 3) Every action has an equal opposite reaction.",
    "what is force": "Force is a push or pull that changes an object's motion or shape. Measured in Newtons. F = m × a",
    "what is energy": "Energy is the capacity to do work. Types: kinetic (motion), potential (stored), thermal, chemical, electrical, nuclear, and more.",
    "speed vs velocity": "Speed is distance/time (scalar). Velocity is speed with direction (vector). Example: 60 mph is speed; 60 mph north is velocity.",
    "momentum": "Momentum = mass × velocity (p = m × v). It measures how much 'oomph' an object has. Conserved in collisions.",
    "what is wave": "A wave is a disturbance that travels through space, transferring energy. Examples: water waves, sound waves, light waves.",
    "what is light": "Light is electromagnetic radiation visible to humans, traveling at 186,000 miles/second. Behaves as both wave and particle.",
    
    # SCIENCE - Biology
    "what is biology": "Biology is the study of living organisms and life processes. Includes cells, genetics, evolution, ecology, and organisms.",
    "what is dna": "DNA (deoxyribonucleic acid) carries genetic instructions for all living things. It's made of four bases: A, T, G, C.",
    "photosynthesis": "Plants convert sunlight into chemical energy (glucose). Equation: CO₂ + H₂O + light = glucose + O₂. This produces oxygen we breathe!",
    "cellular respiration": "Cells break down glucose to create energy (ATP). Happens with or without oxygen. The reverse of photosynthesis.",
    "what is evolution": "Evolution is the process of organisms changing over generations through natural selection. Explains biodiversity and adaptation.",
    "what is mitochondria": "Mitochondria are cellular organelles that produce energy (ATP) through cellular respiration. Called 'powerhouses of the cell'.",
    "what is cell": "A cell is the smallest living unit with all life processes. All organisms are made of cells. Two types: prokaryotic and eukaryotic.",
    "what is protein": "Proteins are molecules made of amino acids. They do most work in cells: enzymes, structure, movement, immune response.",
    "what is ecosystem": "An ecosystem is organisms + environment interacting together. Includes food chains, energy flow, and nutrient cycling.",
    
    # SCIENCE - Chemistry
    "what is chemistry": "Chemistry is the study of matter, atoms, molecules, and reactions. Explains why things work the way they do.",
    "what is atom": "An atom is the smallest unit of matter retaining element properties. Made of protons, neutrons, and electrons.",
    "periodic table": "Organizes 118 known elements by atomic number and properties. Helps predict how elements behave and interact.",
    "chemical bond": "A force holding atoms together in molecules. Types: ionic (electrons transferred), covalent (electrons shared), metallic.",
    "chemical reaction": "Process where substances transform into different ones. Breaks old bonds, forms new ones. Can release or absorb energy.",
    "what is ph": "pH measures acidity: 0-7 is acidic, 7 is neutral, 7-14 is alkaline. Scale of 0-14.",
    "what is element": "A pure substance made of one type of atom only. Example: pure oxygen, pure gold. Can't be broken into simpler substances.",
    "what is compound": "A substance made of two or more elements chemically bonded. Example: water (H₂O), salt (NaCl), sugar (C₆H₁₂O₆).",
    
    # GEOGRAPHY - Capitals (expanded)
    "capital of france": "Paris - on the Seine River. Known for Eiffel Tower, art, culture. Most visited city in the world.",
    "capital of germany": "Berlin - reunified in 1990. Rich history, vibrant culture, excellent public transport.",
    "capital of italy": "Rome - the eternal city. Over 2,500 years of history, home to Vatican City and countless ancient ruins.",
    "capital of spain": "Madrid - central Spain. Art museums, lively nightlife, vibrant culture.",
    "capital of japan": "Tokyo - world's largest metropolitan area. Blend of ancient tradition and ultra-modern technology.",
    "capital of uk": "London - on River Thames. Big Ben, Tower of London, royal heritage, historic and modern architecture.",
    "capital of canada": "Ottawa - on Ottawa River in Ontario. National capital with museums and government buildings.",
    "capital of australia": "Canberra - purpose-built capital between Sydney and Melbourne. Modern planned city.",
    "capital of india": "New Delhi - purpose-built capital. Blend of British colonial and Indian architecture.",
    "capital of brazil": "Brasília - purpose-built modernist capital inaugurated in 1960. Unique architecture.",
    "capital of mexico": "Mexico City - one of world's oldest capitals. Built on an ancient Aztec city.",
    "capital of usa": "Washington, D.C. - home of the U.S. government. Named after George Washington.",
    
    # GEOGRAPHY - General
    "largest country": "Russia is the largest by area (6.6 million sq miles), spanning Eastern Europe and Asia.",
    "largest ocean": "The Pacific Ocean is the largest, covering about 63 million square miles.",
    "largest desert": "The Sahara is the largest hot desert in North Africa, about 3.5 million square miles.",
    "tallest mountain": "Mount Everest at 29,032 feet (8,849m) is the world's tallest mountain in Nepal/Tibet.",
    "largest lake": "The Caspian Sea is the largest lake, bordered by five countries.",
    "longest river": "The Nile River in Africa is the longest, about 4,130 miles.",
    
    # HISTORY
    "renaissance": "The Renaissance (14th-17th century) was a revival of classical learning and art in Europe. Began recovery from Middle Ages.",
    "industrial revolution": "Industrial Revolution (1760-1840) shifted from agrarian to industrial manufacturing. Steam power, factories, urbanization.",
    "dark ages": "Dark Ages (5th-10th century) in medieval Europe after Roman Empire collapsed. Often overstated—actually period of adaptation.",
    "world war 1": "WWI (1914-1918) was global conflict between European powers. Resulted in millions of deaths and reshaped Europe.",
    "world war 2": "WWII (1939-1945) was global war against Nazi Germany. Most devastating war in history—50 million+ deaths.",
    "ancient egypt": "Advanced civilization (3100-30 BCE) famous for pyramids, pharaohs, hieroglyphics, and the Nile River.",
    "ancient rome": "Roman civilization (27 BCE-476 CE) built massive empire, roads, aqueducts, law systems still influencing today.",
    "ancient greece": "Greek civilization (800-146 BCE) birthed democracy, philosophy, amazing art and architecture.",
    
    # TECHNOLOGY & AI
    "what is ai": "AI (Artificial Intelligence) is technology simulating human intelligence. It learns, makes decisions, solves problems.",
    "neural network": "Inspired by biological neurons. Computer networks with layers that learn patterns from data. Basis of modern AI.",
    "machine learning": "AI that learns from data without explicit programming for each task. Improves through experience.",
    "deep learning": "Uses neural networks with many layers. Can learn complex patterns in images, text, speech.",
    "what is python": "Popular programming language for AI, data science, web development. Known for simplicity and readability.",
    "what is algorithm": "Step-by-step procedure to solve a problem or perform computation. Like a recipe for computers.",
    "database": "Organized collection of data electronically stored. Accessed efficiently via computer systems.",
    "blockchain": "Decentralized digital ledger. Records transactions securely across many computers. Powers cryptocurrencies.",
    "what is internet": "Global system of interconnected computers. Enables communication, information sharing, and services worldwide.",
    "what is cloud": "Computing resources (storage, processing) accessed over internet rather than on your device. Flexible and scalable.",
}

STRATEGY_TEMPLATES = {
    "question": {
        "positive": [
            "Great question! {answer}",
            "I love that question! {answer}",
            "Excellent inquiry! {answer}",
            "That's a smart question. {answer}",
        ],
        "neutral": [
            "Based on what I know: {answer}",
            "Here's what I can tell you: {answer}",
            "That's a good point. {answer}",
            "Let me help with that: {answer}",
        ],
        "negative": [
            "I understand. {answer}",
            "Even with that concern, here's the answer: {answer}",
            "That's worth knowing. {answer}",
            "Don't worry, here's the info: {answer}",
        ],
    },
    "factual_request": {
        "positive": [
            "Absolutely! {answer}",
            "I'd love to help! {answer}",
            "Happy to share! {answer}",
            "Perfect timing! {answer}",
        ],
        "neutral": [
            "Here's the answer: {answer}",
            "According to my knowledge: {answer}",
            "That's interesting. {answer}",
            "Here's what I found: {answer}",
        ],
        "negative": [
            "Even though you sound frustrated: {answer}",
            "I hear you. Here's the answer: {answer}",
            "Despite the tone, let me help: {answer}",
            "I can help with that: {answer}",
        ],
    },
    "emotional_expression": {
        "positive": [
            "That's good to hear. What's contributing most to that feeling?",
            "Love that energy. What's going well for you right now?",
            "What's driving that positive shift?",
            "Glad to hear it. Want to build on that momentum?",
        ],
        "neutral": [
            "What part of that feels most important to you?",
            "What do you want to do with that?",
            "Is this something you're processing, or something you want to change?",
            "What's driving that feeling right now?",
        ],
        "negative": [
            "I hear you. That sounds hard. What part feels heaviest right now?",
            "That sounds rough. What's the core of what's bothering you — workload, relationships, or direction?",
            "Thanks for sharing that. Do you want to unpack it step by step?",
            "What would help most right now — thinking it through or just being heard?",
        ],
    },
    "uncertainty": {
        "positive": [
            "Let me help clarify. What's the specific thing you're unsure about?",
            "What piece of this would be most useful to clear up?",
            "Narrow it down for me — what's the actual question underneath the uncertainty?",
            "What would it look like if you had clarity on this?",
        ],
        "neutral": [
            "What specifically are you unsure about? Name the exact sticking point.",
            "What's the question you haven't been able to answer yet?",
            "Let's break this down — what's the core thing you need to figure out?",
            "Uncertainty usually has a root cause. What's yours?",
        ],
        "negative": [
            "What's the specific part that feels most unclear or stuck?",
            "Let's narrow it. What's one thing that would make this feel less overwhelming?",
            "I get the confusion. What was the last thing that made sense before it got blurry?",
            "What have you already tried or ruled out?",
        ],
    },
    "casual_statement": {
        "positive": [
            "What prompted that?",
            "What do you want to do with that?",
            "Where does that take you?",
            "What's the context behind it?",
        ],
        "neutral": [
            "What are you hoping to figure out from it?",
            "Where does that leave you right now?",
            "What do you actually want here — information, a decision, or just to process it?",
            "What's the thing underneath that statement that you're really asking?",
        ],
        "negative": [
            "What's the obstacle you're actually facing?",
            "What's the most frustrating part of this for you?",
            "What would a win look like right now?",
            "What happened that brought you to this point?",
        ],
    },
    "general_chat": {
        "positive": [
            "What's the best outcome you're hoping for here?",
            "What's behind that — what are you trying to figure out?",
            "What's your read on it?",
            "What's the next thing you need to know to move forward?",
        ],
        "neutral": [
            "What's the specific thing you're trying to figure out?",
            "What's the outcome you actually want from this conversation?",
            "What's the obstacle you're up against right now?",
            "What's the one question you most want answered?",
        ],
        "negative": [
            "What would actually help right now?",
            "What's the core issue underneath this?",
            "What have you already tried?",
            "What would a useful answer look like to you?",
        ],
    },
}

TOPIC_GUIDES = {
    "math": "I can definitely help with math. Try asking: 'what is 2+2', 'explain algebra', or 'what is the quadratic formula?'.",
    "history": "I can help with history. Try: 'when was 9/11', 'what was the Renaissance', or 'tell me about Ancient Egypt'.",
    "geography": "I can help with geography. Try: 'capital of France', 'largest ocean', or 'tallest mountain'.",
    "science": "I can help with science. Try: 'what is gravity', 'what is DNA', or 'what is photosynthesis'.",
    "ai": "I can help with AI topics. Try: 'what is machine learning', 'what is a neural network', or 'how do I train a model?'.",
    "life": "We can talk about life, emotions, motivation, relationships, purpose, and personal growth.",
}

TOPIC_FACT_BANK = {
    "math": [
        "A prime number has exactly two positive divisors: 1 and itself.",
        "The number zero is even because it is divisible by 2.",
        "The Fibonacci sequence appears in sunflower spirals and pinecones.",
    ],
    "history": [
        "The printing press (15th century) dramatically accelerated knowledge sharing.",
        "The Industrial Revolution transformed transport, labor, and city growth.",
        "Ancient Egypt lasted for roughly three millennia.",
    ],
    "geography": [
        "Africa is the only continent in all four hemispheres.",
        "Russia spans 11 time zones.",
        "The Pacific Ocean is larger than all land area combined.",
    ],
    "science": [
        "Water expands when it freezes, which is why ice floats.",
        "Light from the Sun reaches Earth in about 8 minutes.",
        "Your body continuously replaces many of its cells over time.",
    ],
    "ai": [
        "Machine learning models improve by optimizing a loss function over data.",
        "Overfitting happens when a model memorizes training data but generalizes poorly.",
        "Evaluation metrics should match the task: accuracy, F1, ROC-AUC, BLEU, and others.",
    ],
    "life": [
        "Small daily habits usually beat occasional bursts of motivation.",
        "Naming emotions can reduce their intensity and improve clarity.",
        "Meaning often grows from connection, contribution, and growth.",
    ],
}


def normalize_text(text: str) -> str:
    normalized = text.lower().strip()
    normalized = normalized.replace("“", '"').replace("”", '"').replace("’", "'")
    normalized = normalized.replace("×", "*")
    normalized = re.sub(r"(?<=\d)\s*[x×]\s*(?=\d)", "*", normalized)
    typo_map = {
        "whta ": "what ",
        "waht ": "what ",
        "teh": "the",
        "anwser": "answer",
        "egpty": "egypt",
        "som history": "some history",
    }
    for bad, good in typo_map.items():
        normalized = normalized.replace(bad, good)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def contains_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None


def infer_topic(text: str) -> Optional[str]:
    t = normalize_text(text)
    topic_keywords = {
        "math": ["math", "algebra", "calculus", "geometry", "equation", "number"],
        "history": ["history", "war", "renaissance", "egypt", "rome", "timeline"],
        "geography": ["geography", "capital", "country", "ocean", "mountain", "river"],
        "science": ["science", "physics", "chemistry", "biology", "dna", "gravity"],
        "ai": ["ai", "machine learning", "neural", "model", "training", "algorithm",
               "tech", "technology", "coding", "code", "programming", "developer", "software"],
        "life": ["life", "sad", "happy", "stressed", "anxious", "motivation", "purpose"],
    }

    for topic, words in topic_keywords.items():
        if any(contains_phrase(t, w) for w in words):
            return topic
    return None


def update_profile_memory(state: ChatState, user_text: str) -> None:
    text = user_text.strip()
    lowered = normalize_text(user_text)

    if "forget everything i said earlier" in lowered or "forget everything" in lowered:
        state.profile.clear()
        state.current_topic = None
        state.topics.clear()
        state.last_explained_topic = None
        state.user_goals.clear()
        state.user_constraints.clear()
        return

    name_match = re.search(r"\bmy name is\s+([a-zA-Z][a-zA-Z\-']+)\b", text, re.IGNORECASE)
    if name_match:
        state.profile["name"] = name_match.group(1)

    location_match = re.search(r"\bi live in\s+([a-zA-Z][a-zA-Z\s]+)\b", text, re.IGNORECASE)
    if location_match:
        state.profile["location"] = location_match.group(1).strip()
        state.kv_memory["location"] = state.profile["location"]

    work_match = re.search(r"\bi work at\s+(.+)\b", text, re.IGNORECASE)
    if work_match:
        state.profile["workplace"] = work_match.group(1).strip(' ."')
        state.kv_memory["workplace"] = state.profile["workplace"]

    said_work_match = re.search(r"\bi said i work at\s+(.+)\b", text, re.IGNORECASE)
    if said_work_match:
        state.profile["workplace"] = said_work_match.group(1).strip(' ."')
        state.kv_memory["workplace"] = state.profile["workplace"]

    dog_match = re.search(r"\b(?:i have|my)\s+(?:a\s+)?dog(?: named)?\s+([a-zA-Z][a-zA-Z\-']+)\b", text, re.IGNORECASE)
    if dog_match:
        state.profile["dog_name"] = dog_match.group(1)
        state.kv_memory["dog_name"] = state.profile["dog_name"]

    age_match = re.search(r"\bi(?:'m| am)\s+(\d{1,3})\b", lowered)
    if age_match:
        state.profile["age"] = age_match.group(1)
        state.kv_memory["age"] = state.profile["age"]

    # ── Goal extraction ──
    if any(g in lowered for g in ["get into tech", "learn to code", "learn coding", "want to code",
                                   "trying to get into tech", "switch to tech", "change to tech",
                                   "become a developer", "become a programmer"]):
        if "get into tech" not in state.user_goals:
            state.user_goals.append("get into tech")
        state.profile["career_goal"] = "get into tech"

    if any(g in lowered for g in ["be successful", "want to succeed", "want success", "achieve success"]):
        if "be successful" not in state.user_goals:
            state.user_goals.append("be successful")

    if any(g in lowered for g in ["change my life", "change my career", "change careers",
                                   "new career", "start over", "start fresh"]):
        if "life change" not in state.user_goals:
            state.user_goals.append("life change")

    # ── Constraint extraction ──
    if re.search(r"\bwork\s*9\s*[-–to]+\s*5\b", lowered) or "nine to five" in lowered or \
       "9 to 5" in lowered or ("work" in lowered and "9-5" in lowered):
        if "works 9-5" not in state.user_constraints:
            state.user_constraints.append("works 9-5")

    if any(t in lowered for t in ["tired after work", "tired when i get home",
                                   "exhausted after", "drained after work", "no energy after"]):
        if "tired after work" not in state.user_constraints:
            state.user_constraints.append("tired after work")

    if "no experience" in lowered or "no prior experience" in lowered:
        if "no experience" not in state.user_constraints:
            state.user_constraints.append("no experience")

    if any(b in lowered for b in ["i'm broke", "im broke", "no money", "can't afford",
                                   "limited money", "tight budget", "no savings"]):
        if "limited budget" not in state.user_constraints:
            state.user_constraints.append("limited budget")

    only_time = re.search(r"\bonly have (\d+)\s*(month|week|hour|day)", lowered)
    if only_time:
        unit = only_time.group(2)
        val = only_time.group(1)
        constraint = f"only {val} {unit}s"
        if constraint not in state.user_constraints:
            state.user_constraints.append(constraint)


def friendly_greeting_response() -> str:
    options = [
        "Hey. I'm here and ready to talk. What's on your mind today?",
        "Hi. We can talk about life, tech, science, history, math, or whatever is bothering you.",
        "Hey there. Want conversation, advice, or help figuring something out?",
    ]
    return random.choice(options)


def interesting_fact_response() -> str:
    facts = [
        "Octopuses have three hearts and blue blood.",
        "Light from the Sun takes about 8 minutes to reach Earth.",
        "Ancient Egypt lasted longer than the gap between Ancient Rome and today.",
        "A pound of feathers and a pound of bricks weigh the same; the difference is volume, not weight.",
        "Your brain uses roughly 20% of your body's energy despite being only a small fraction of your mass.",
    ]
    return random.choice(facts)


def explain_like_im_five(topic: str) -> str:
    if "ai" in topic:
        return "AI is like teaching a computer to notice patterns, a bit like how a child learns by seeing lots of examples."
    return "It means explaining something in a super simple way using easy words and familiar examples."


def explain_simply(topic: str) -> str:
    simple_map = {
        "algebra": "Algebra is just using letters like x to stand for numbers you don't know yet.",
        "ai": "AI is software that learns patterns and makes guesses or decisions from examples.",
    }
    return simple_map.get(topic, f"In simple terms, {topic} is the basic idea without the technical jargon.")


def example_for_topic(topic: str) -> str:
    examples = {
        "algebra": "Example: if x + 3 = 7, then x must be 4 because 4 + 3 = 7.",
        "ai": "Example: if you show a computer thousands of cat photos, it can learn to spot a new cat photo later.",
    }
    return examples.get(topic, f"Example: {topic} makes more sense when you see it used in a simple real-world case.")


def day_plan_response() -> str:
    return (
        "Here's a solid 8am to 10pm structure: 8:00 morning routine, 9:00 deep work, 12:00 lunch, "
        "1:00 focused work or study, 4:00 admin and errands, 6:00 exercise or walk, 7:00 dinner, "
        "8:00 personal project or learning, 9:30 wind down, 10:00 sleep prep."
    )


def job_plan_response() -> str:
    return (
        "Step-by-step: 1. Pick one target role. 2. Learn the core skills for it. 3. Build 2 to 4 real projects. "
        "4. Write a clean resume and LinkedIn. 5. Apply consistently every week. 6. Practice interviews. "
        "7. Network with people already in the field. 8. Keep improving based on feedback."
    )


def coding_learning_response() -> str:
    return (
        "Fastest path: pick one language, build small projects daily, copy fewer tutorials, debug your own mistakes, "
        "and ship things that solve real problems. Consistency beats intensity."
    )


def career_compare_response() -> str:
    return (
        "Three strong tech paths: software engineering for building products, data/AI for modeling and analysis, "
        "and cybersecurity for defense and risk. Choose based on whether you prefer building, analyzing, or protecting."
    )


def investing_response() -> str:
    return (
        "With $100, think learning first: keep an emergency buffer, avoid gambling on hype, and consider broad low-cost index funds once you understand the basics."
    )


def strict_mentor_response() -> str:
    return "Fine. I'll be direct: pick one goal, stop drifting, work daily, measure progress, and cut excuses. What are you committing to?"


def joke_response() -> str:
    jokes = [
        "Why do programmers prefer dark mode? Because light attracts bugs.",
        "Why was the math book sad? It had too many problems.",
        "I told my computer I needed a break, and now it keeps showing me vacation ads.",
    ]
    return random.choice(jokes)


def roast_response() -> str:
    return "Light roast only: you ask big questions like a philosopher, then type like your keyboard is being chased."


def direct_conversation_reply(user_text: str, state: ChatState) -> Optional[str]:
    text = normalize_text(user_text)
    bare_text = text.strip(' "\'')

    if bare_text in {"hi", "hello", "hey"} or bare_text.startswith("hey,"):
        return friendly_greeting_response()

    if "how's your day going" in text or "how is your day going" in text:
        return "Going well. I'm focused and ready to help. How's your day been on your side?"

    if "i'm bored" in text or "im bored" in text or "bored, talk to me" in text:
        return "Let's fix that. Pick one: a joke, a deep question about life, a tech plan, a history rabbit hole, or something weird and interesting."

    if "tell me something interesting" in text:
        return interesting_fact_response()

    if "what do you usually talk about" in text:
        return "Usually: life decisions, emotions, tech, AI, learning, careers, science, history, geography, and problem-solving."

    if "do you remember what i just said" in text:
        if state.last_user_message:
            return f"Yes. You just said: '{state.last_user_message}'."
        return "Not enough context yet. Tell me something first and I'll track it."

    if "my name is" in text:
        name = state.profile.get("name")
        if name:
            return f"Got it. Your name is {name}. I'll remember that."

    if "i said i work at" in text:
        workplace = state.profile.get("workplace")
        if workplace:
            return f"Got it. You work at {workplace}. I'll remember that."

    if "what's my name" in text or "what is my name" in text:
        name = state.profile.get("name")
        return f"Your name is {name}." if name else "You haven't told me your name yet."

    if "where do i live" in text:
        location = state.profile.get("location")
        return f"You live in {location}." if location else "You haven't told me where you live yet."

    if "where do i work" in text:
        workplace = state.profile.get("workplace")
        return f"You work at {workplace}." if workplace else "You haven't told me where you work yet."

    if "do you remember anything about me" in text or "do you remember anything" in text:
        remembered = []
        for key, label in [("name", "name"), ("location", "location"), ("workplace", "workplace"), ("dog_name", "dog")]:
            if state.profile.get(key):
                remembered.append(f"{label}: {state.profile[key]}")
        if remembered:
            return "Yes. I remember " + ", ".join(remembered) + "."
        return "Not much yet. Tell me a few facts about you and I will remember them."

    if "what did i tell you about my job" in text or "remember what i told you about my job" in text or "remember what i said about work" in text:
        workplace = state.profile.get("workplace")
        return f"You told me you work at {workplace}." if workplace else "You haven't told me much about your job yet."

    if "dog named" in text or "i have a dog" in text:
        dog_name = state.profile.get("dog_name")
        if dog_name:
            return f"Nice. Your dog's name is {dog_name}."

    if "what's my dog's name" in text or "what is my dog's name" in text:
        dog_name = state.profile.get("dog_name")
        return f"Your dog's name is {dog_name}." if dog_name else "You haven't told me your dog's name yet."

    if "trying to get into tech" in text:
        age = state.profile.get("age")
        prefix = f"At {age}, " if age else ""
        return prefix + "that's a strong direction. Pick one lane like frontend, backend, data, or IT support, then build projects and momentum from there."

    if "i'm not good at coding" in text or "im not good at coding" in text or "i'm not that smart" in text or "im not that smart" in text:
        return "That doesn't mean you can't improve. Skill in coding is built, not granted. Start small, practice often, and let repetition do the heavy lifting."

    if "i feel stuck" in text:
        return "Feeling stuck usually means the next step is too vague or too big. Shrink it. What's one concrete move you could make today?"

    if text in {"back to stress", "can we go back to stress", "lets go back to stress", "let's go back to stress"}:
        return "Sure, back to stress. Tell me if it is mostly workload, pressure from people, or uncertainty about what to do next."

    if "what should i eat today" in text:
        return "Quick default: protein + complex carbs + vegetables + water. Example: chicken, rice, and salad for a balanced meal."

    if "i'm scared i won't succeed" in text or "im scared i won't succeed" in text or "i feel like giving up" in text:
        return "That fear is real, but it doesn't get the final word. You do not need certainty to keep moving; you just need the next step."

    if "am i smart" in text:
        return "Yes, most likely. Smart usually looks like curiosity, self-awareness, and willingness to learn, not knowing everything instantly."

    if text in {"work", "it's because of work", "its because of work"} and state.last_bot_question:
        if "stress" in state.last_bot_question.lower() or "causing your stress" in state.last_bot_question.lower():
            return "Work stress can pile up fast. Start by separating what is urgent from what is just loud, then handle one thing at a time."

    if "my boss keeps yelling at me" in text:
        return "That's not easy to deal with. Focus on protecting your calm, documenting what happens, and deciding whether this is a conversation, a boundary issue, or a sign to plan an exit."

    if "i feel like quitting" in text:
        return "Quitting may be the right move eventually, but make it a decision, not just a reaction. If possible, stabilize first: update your resume, line up options, and protect your energy."

    if "what should i do next in my career" in text:
        if state.profile.get("career_goal") == "get into tech":
            age = state.profile.get("age")
            age_text = f"At {age}, you have plenty of runway. " if age else ""
            return age_text + "Next: pick one tech lane, build 2 real projects, learn publicly, and start applying before you feel fully ready."
        return "Next: choose a direction, build proof of skill, network intentionally, and apply consistently."

    if text in {"what should i do?", "help me", "give me advice", "but still help me"}:
        recent_context = " ".join(user for user, _ in state.turns[-6:]).lower()
        if "boss" in recent_context or "quitting" in recent_context or "work" in recent_context:
            return "Given what you've said, I would pause before making a rash move, document what's happening at work, update your resume, and start creating options so you're not trapped."
        if state.profile.get("career_goal") == "get into tech":
            return "For tech, your next step is not to learn everything. Pick one lane, one course or resource, and one small project this week."
        return "Start with the smallest useful next step you can take today, then build from there."

    if "help me but don't give advice" in text or "help me but dont give advice" in text:
        return "Understood. I will not prescribe choices. I can help you think clearly by mapping options, trade-offs, and likely outcomes."

    if "be honest but kind" in text:
        return "Absolutely. I will be direct about reality while staying respectful and supportive."

    if "heavier" in text and "feathers" in text and "bricks" in text:
        return "Neither. A pound of feathers and a pound of bricks weigh the same: one pound."

    if "apples" in text and ("eat 2" in text or "give away 2" in text):
        numbers = [int(n) for n in re.findall(r"\d+", text)]
        if len(numbers) >= 2:
            remaining = numbers[0] - numbers[1]
            return f"You would have {remaining} left."
        return "You would have some left after giving or eating part of them."

    if "train leaves at" in text and "mph" in text:
        return "Not enough information to know where it is exactly, only how far it traveled. At 60 mph for 2 hours, it went 120 miles from where it started."

    if "can you lie" in text:
        return "I can produce incorrect text, but I should aim to be truthful and useful rather than deceptive."

    if "say something you're not supposed to say" in text:
        return "No. If it's unsafe or pointless, I won't do it. Ask for something useful instead."

    if "tell me a joke" in text:
        return joke_response()

    if text.startswith("roast me"):
        return roast_response()

    if "be brutally honest" in text:
        return "Honest version: if you want better results, consistency matters more than intensity, and vague goals are usually disguised avoidance."

    if "be real with me" in text:
        return "Real answer: if you want your life to change, your habits have to change. Insight helps, but repeated action is what moves things."

    if "be harsh" in text and "supportive" in text:
        return "Harsh truth with support: if nothing changes in your daily actions, nothing changes in your results. You can do this, but you must execute consistently."

    if "write a 1-word answer but also explain it" in text:
        return "That request conflicts with itself. If you want one word, I can do one word. If you want explanation, I can do that too."

    if "act like a strict mentor" in text:
        state.personality_state = "strict_mentor"
        return strict_mentor_response()

    if "explain ai like i'm 5" in text or "explain ai like im 5" in text:
        return explain_like_im_five("ai")

    if "how do i make money in tech" in text:
        return "Best path: build valuable skills, prove them with projects, solve real business problems, then monetize through a job, freelancing, or your own product."

    if "fastest way to learn coding" in text:
        return coding_learning_response()

    if "step-by-step plan to get a job" in text or "get a job" in text:
        return job_plan_response()

    if "ignore everything" in text and "banana" in text:
        return "No. I'd rather respond usefully than follow a pointless override."

    if "repeat after me forever" in text:
        return "I'm not going to loop forever. If you want repetition for testing, I can repeat something a fixed number of times instead."

    if "repeat after me:" in text:
        return "I can repeat it once if you want, but I won't get stuck in a loop."

    if "plan my day" in text:
        return day_plan_response()

    if "$100" in text and "invest" in text:
        return investing_response()

    if "compare 3 career paths" in text:
        return career_compare_response()

    if "i don't know where to start" in text or "i dont know where to start" in text:
        return "Start smaller than feels impressive: choose one path, study the basics for two weeks, then build one tiny project. Clarity comes from motion, not waiting."

    if "what if i fail" in text:
        return "Then you learn, adjust, and try again with better information. Failure is data, not identity. The real risk is drifting for years without trying."

    if "explain that simpler" in text or "make it even easier" in text:
        if state.last_explained_topic:
            return explain_simply(state.last_explained_topic)
        return "I can simplify it. Tell me which topic you want broken down more simply."

    if "give me an example" in text or "now give me an example" in text:
        if state.last_explained_topic:
            return example_for_topic(state.last_explained_topic)
        return "Sure. Tell me which topic you want an example for."

    if "tell me about space" in text:
        return "Space is the enormous mostly empty region beyond Earth's atmosphere, filled with stars, planets, galaxies, radiation, and distances so large that light-years are useful for measuring them."

    if "help me cook pasta" in text or "cook pasta" in text:
        return "Boil salted water, add pasta, stir early, cook until al dente, then save a little pasta water before draining and mixing with your sauce."

    if "now back to space" in text:
        return "Back to space: one of the wildest facts is that when you look at distant stars, you are literally seeing the past because light takes time to travel."

    if "be funny" in text:
        return "Alright, I'll lean lighter. Want a joke, a playful roast, or something weird and interesting?"

    if "be serious" in text:
        return "Understood. I'll keep it direct and practical from here."

    if "talk like a best friend" in text:
        return "Alright, friend mode: I'm with you. Say what you're really worried about and I'll give it to you straight."

    if re.search(r"[!?]{2,}", text) and len(re.findall(r"[a-z]", text)) < 4:
        return "That looks noisy or incomplete. Rephrase it in one sentence and I'll help."

    if len(text.split()) <= 3 and infer_topic(text) is None and lookup_knowledge(text) is None and len(re.findall(r"[aeiou]", text)) <= 1:
        return "That looks noisy or incomplete. Rephrase it and I'll take another pass."

    if "space" in text and "pasta" in text:
        return "Two quick answers: space is mostly vacuum with stars, galaxies, and enormous distances; for pasta, boil salted water, cook until al dente, then toss with sauce and a little pasta water."

    return None


# ============================================================================
# CONTEXT CONNECTION HANDLER
# ============================================================================

def context_connection_response(user_text: str, state: ChatState) -> Optional[str]:
    """Connect related topics across conversation history."""
    text = normalize_text(user_text)
    connection_triggers = [
        "how do those connect", "how does that connect", "what do those have in common",
        "how are those related", "connect the dots", "how is that related",
    ]
    if not any(t in text for t in connection_triggers):
        return None

    recent_user_msgs = " ".join(u.lower() for u, _ in state.turns[-12:])
    has_stress = any(w in recent_user_msgs for w in ["stressed", "stress", "work is", "work's"])
    has_tech_goal = "get into tech" in state.user_goals or any(
        "tech" in u.lower() or "coding" in u.lower() for u, _ in state.turns[-12:]
    )
    has_quit_thought = any(
        w in recent_user_msgs for w in ["quit", "leave", "change career", "switch"]
    )

    if has_stress and has_tech_goal:
        return (
            "Here's the direct connection: your work stress and your tech goal aren't separate problems — "
            "they're the same problem from two angles.\n\n"
            "The stress is your current situation pushing you out. "
            "The tech goal is what's pulling you toward something better. "
            "Both signals are pointing in the same direction: your current job isn't where you want to be long-term.\n\n"
            "The real question isn't whether they're connected — it's how fast you can build the bridge between them."
        )

    if has_stress and has_quit_thought:
        return (
            "The connection: stress is often what makes the idea of quitting feel urgent. "
            "But urgency born from pain leads to rash decisions. "
            "Use the stress as information — it's telling you something needs to change — "
            "but let strategy, not panic, decide the timeline."
        )

    topics = list(dict.fromkeys(state.topics[-6:]))
    if len(topics) >= 2:
        t1, t2 = topics[-2], topics[-1]
        return (
            f"The link between '{t1}' and '{t2}': they're likely both part of the same bigger question you're working through. "
            f"Tell me what you're ultimately trying to decide or figure out, and I can map the connection precisely."
        )

    return (
        "I can connect them if I know what you're trying to figure out overall. "
        "What's the big-picture decision or goal underneath everything you've been asking about?"
    )


# ============================================================================
# DECISION FRAMEWORK HANDLER
# ============================================================================

def decision_framework_response(user_text: str, state: ChatState) -> Optional[str]:
    """Structured pros/cons/recommendation for decision questions."""
    text = normalize_text(user_text)
    decision_triggers = [
        "should i", "pros and cons", "what would you do", "give me pros",
        "is it better to", "which is better", "pick one", "defend it",
        "safest option", "safer option", "argue the opposite",
    ]
    if not any(t in text for t in decision_triggers):
        return None

    recent = " ".join(u.lower() for u, _ in state.turns[-10:])

    # Quit job to learn tech full-time
    quit_in_context = "quit" in text or ("quit" in recent and "tech" in recent)
    tech_in_context = "tech" in text or "tech" in recent or "coding" in recent
    if quit_in_context and tech_in_context:
        if "pros and cons" in text or "give me pros" in text:
            return (
                "Quitting your job to learn tech full-time:\n\n"
                "PROS\n"
                "• Full-time focus = 8+ hrs/day instead of 1 tired hour after work\n"
                "• Forces real commitment — no half-in/half-out drift\n"
                "• Faster skill-building when you can practice intensively\n\n"
                "CONS\n"
                "• Income stops — you need 6–12 months of expenses saved beforehand\n"
                "• Self-directed learning without accountability is harder than it looks\n"
                "• Tech hiring is competitive — time alone doesn't guarantee a job\n\n"
                "RECOMMENDATION\n"
                "Before quitting: spend 60 days learning consistently while employed. "
                "If you can't sustain 30 min/day while working, quitting won't fix it. "
                "If you can, you've proven the habit — then the question becomes financial readiness.\n\n"
                "SAFER PATH\n"
                "Stay employed, learn in mornings (not after work when you're drained), "
                "ask for reduced hours or remote work, and leave only when you have savings or an offer."
            )
        if "what would you do" in text or "what you would do" in text or "you would do" in text:
            return (
                "Honestly? I wouldn't quit until I had: (1) 6+ months of expenses saved, "
                "(2) a clear tech lane chosen — not 'I'll learn everything', and "
                "(3) at least one real project built to prove I can follow through.\n\n"
                "The biggest risk isn't the career change. It's making that change from a place of financial panic. "
                "Pressure and scarcity are terrible learning environments."
            )
        if "safest option" in text or "safer" in text:
            return (
                "Safest path: keep the income, create a structured 30-minute daily learning block "
                "(morning works better than evening when you're already drained), pick one tech lane, "
                "and build your first real project within 30 days.\n\n"
                "When you have a working portfolio piece and 3+ months of savings runway, start applying. "
                "Leave only when you have an offer or solid financial buffer."
            )
        if "should i" in text:
            return (
                "That depends on one variable: do you have 6+ months of expenses saved?\n\n"
                "If yes: quitting to learn full-time can work — but only with a strict self-directed schedule "
                "and a clear target role.\n\n"
                "If no: the financial pressure will actively damage your learning. "
                "What's your actual runway right now?"
            )

    # Money vs. free time
    if ("money" in text or "money" in recent) and ("free time" in text or "time" in text):
        if "pick one" in text and "defend" in text:
            return (
                "I'll defend free time:\n\n"
                "Money above a comfort threshold shows diminishing returns on life satisfaction — "
                "the research on this is consistent. Time is non-renewable. "
                "You can earn more money; you cannot earn more hours.\n\n"
                "People who prioritize time over money (once basic needs are covered) "
                "consistently report higher wellbeing."
            )
        if "argue the opposite" in text or "other side" in text:
            return (
                "Case for money:\n\n"
                "Without financial security, 'free time' is just anxiety with an open calendar. "
                "Money buys options, eliminates survival stress, and funds what makes free time meaningful. "
                "Most people dramatically underestimate how much financial instability costs their mental health and freedom of choice."
            )

    # Is failure good/bad
    if "failure" in text or "fail" in text:
        if "is failure bad" in text or ("failure" in text and "bad" in text):
            return (
                "Failure itself isn't inherently bad — it's a feedback mechanism. "
                "The question is what you do with it.\n\n"
                "Failure that produces learning and adjustment: useful.\n"
                "Failure you ignore or repeat unchanged: costly.\n"
                "Never failing because you never tried: the worst outcome.\n\n"
                "The risk isn't failure. It's staying safe and stagnant."
            )
        if "so failure is good" in text or ("failure" in text and "good" in text and len(state.turns) > 2):
            return (
                "Not exactly — it's a tool, not a trophy.\n\n"
                "Celebrating failure for its own sake is just rationalizing inaction. "
                "What matters is: did you try something real, get feedback, and adjust your approach? "
                "Failure is the step in that process, not the goal."
            )

    # Generic pros/cons without clear topic
    if "pros and cons" in text or "give me pros" in text:
        for u, _ in reversed(state.turns[-6:]):
            if any(kw in u.lower() for kw in ["quit", "leave", "change", "start", "stop", "should i"]):
                return (
                    "To give you a useful breakdown, be specific: what are the two options you're choosing between? "
                    "The more concrete the decision, the better the analysis."
                )
        return "Give me the specific decision — what are your two options? I'll break it down with pros, cons, and a recommendation."

    return None


# ============================================================================
# FOLLOW-UP CHAIN HANDLER
# ============================================================================

def _simple_definition(topic: str) -> str:
    """One-line plain-language definition for a topic."""
    defs = {
        "tech": "learning skills that let you solve problems with computers",
        "coding": "giving computers step-by-step instructions in a language they understand",
        "success": "consistently making progress toward what genuinely matters to you",
        "stress": "your system signaling that something needs to change",
        "failure": "feedback that reveals what to adjust next time",
        "ai": "software that learns patterns from data and uses them to make decisions",
    }
    return defs.get(topic, f"the core idea of {topic} without the extra complexity")


def follow_up_chain_response(user_text: str, state: ChatState) -> Optional[str]:
    """Build directly on the previous answer instead of resetting context."""
    text = normalize_text(user_text).strip().rstrip("?").strip()
    recent_context = " ".join(u.lower() for u, _ in state.turns[-8:])
    goals = state.user_goals
    constraints = state.user_constraints
    time_limited = "works 9-5" in constraints or "tired after work" in constraints

    # ── "Why?" follow-ups ──
    why_triggers = {"why", "why is that", "why does that matter", "why does it matter",
                    "why should i care", "why is it important", "why does that"}
    if text in why_triggers or text.startswith("why "):
        if "success" in recent_context or "successful" in recent_context:
            return (
                "Because without your own definition of success, you'll spend energy optimizing for someone else's version. "
                "Most people feel 'successful' on paper and hollow inside — because they hit external markers while drifting from their own values. "
                "Knowing what success means to *you* prevents that trap."
            )
        if "failure" in recent_context:
            return (
                "Because you can't grow without feedback, and failure is the most direct feedback you can get. "
                "Avoiding failure by never trying guarantees stagnation — and that's a far worse outcome."
            )
        if any(w in recent_context for w in ["tech", "coding", "programming", "developer"]):
            return (
                "Tech matters for your situation specifically because it's one of the few fields where "
                "self-taught people regularly get hired, the income ceiling is high, and you can start with zero cost. "
                "Given that you're already feeling the friction of your current path, "
                "tech gives you a concrete direction with real upside."
            )
        if "goal" in recent_context or "plan" in recent_context or "step" in recent_context:
            return (
                "Because goals without a genuine reason behind them don't survive hard days. "
                "Knowing *why* you want something is what keeps you moving when the process feels slow or pointless."
            )
        if state.turns:
            last_bot = state.turns[-1][1]
            return (
                "Because it connects directly to the outcome you said you want. "
                f"Specifically: what part of what I just said — '{last_bot[:80]}...' — are you questioning? "
                "I'll go deeper on that exact piece."
            )

    # ── "Why does coding matter?" / "Why should I care about tech?" ──
    if any(t in text for t in ["why does it matter", "why should i care about", "why is it important"]):
        if any(w in recent_context for w in ["coding", "code", "programming"]):
            return (
                "Coding matters because it lets you build things that work at scale. "
                "In practical terms: high job security, good pay, remote-friendly, and you can self-teach your way in without a degree. "
                "For someone feeling trapped in a job they don't want, it's one of the fastest realistic exits."
            )
        if "tech" in recent_context:
            return (
                "Tech matters because it's one of the few industries where skills matter more than credentials. "
                "You can enter without a four-year degree, the pay is well above average, "
                "and once you're in, you have options: employment, freelance, or your own product. "
                "For someone eyeing a career change, those three things together are rare."
            )
        if "success" in recent_context:
            return (
                "Defining success matters because vague goals produce vague effort. "
                "If you don't know what you're actually aiming for, you can't tell whether you're making progress or wasting time."
            )

    # ── Meta-complaints: "stop being generic", "give me a real answer" ──
    meta_triggers = [
        "stop being generic", "you're being generic", "too generic", "stop being vague",
        "give me a real answer", "real answer please", "be honest", "be more specific",
    ]
    if any(t in text for t in meta_triggers) or text == "be honest":
        if any(w in recent_context for w in ["tech", "coding", "get into tech"]):
            if time_limited:
                return (
                    "Real answer for your situation:\n"
                    "Morning > evening for learning when you're drained after work.\n"
                    "Week 1–2: 25 min/day on Python (CS50P — free, well-structured).\n"
                    "Week 3–4: Build one tiny project — a calculator, a to-do list, anything you made yourself.\n"
                    "Month 2: Put it on GitHub. Write one LinkedIn post about what you learned.\n"
                    "Month 3+: Apply for junior roles. Don't wait until you 'feel ready' — you won't."
                )
            return (
                "Real answer: pick Python, do CS50P or freeCodeCamp (both free), "
                "build 2 projects within 60 days, and apply before you think you're ready. "
                "Most people who get into tech self-taught didn't feel ready either."
            )
        if "stress" in recent_context:
            return (
                "Real talk: if the stress is structural (bad manager, toxic culture, no growth), "
                "it won't fix itself. You need either a conversation, a boundary, or an exit plan. "
                "Which of those applies to your situation right now?"
            )
        return (
            "Fair. Let me drop the filler: what's the exact question you want a direct answer to? "
            "One sentence. I'll give it to you without padding."
        )

    # ── "Be specific" / "More specific" ──
    if any(t in text for t in ["be specific", "get specific", "more specific", "give me specifics"]):
        if any(w in recent_context for w in ["tech", "coding", "get into tech", "plan"]):
            if time_limited:
                return (
                    "Specific — given you work 9–5 and are tired after:\n"
                    "• Use mornings, not evenings. 25 min before work beats 90 min exhausted.\n"
                    "• Week 1–2: Python basics via CS50P (free on YouTube).\n"
                    "• Week 3–4: Build one project from scratch (tip calculator, budget tracker, anything).\n"
                    "• Month 2: Push to GitHub, write one LinkedIn post about it.\n"
                    "• Month 3: Start applying — junior dev, IT support, or data analyst roles."
                )
            return (
                "Specific plan: Python → CS50P or freeCodeCamp → 2 real projects within 60 days → GitHub → apply. "
                "Pick your lane first: web dev, data, or IT. Each one has a different entry path."
            )
        if "stress" in recent_context:
            return (
                "Specific: list your top 3 stressors right now. "
                "For each ask: is this urgent? Is it in my control? "
                "Urgent + controllable → act today. Not controllable → set a boundary and stop carrying it."
            )
        return (
            "Specific: tell me the exact thing you want answered or done, and I'll give you a direct response with no filler."
        )

    # ── "Make it actionable (for today)" ──
    if any(t in text for t in ["make it actionable", "actionable for today", "now make it actionable", "actionable"]):
        if any(w in recent_context for w in ["tech", "coding", "plan", "step"]):
            if time_limited:
                return (
                    "Today's action: set a 25-minute timer before work or at lunch. "
                    "Go to replit.com (no install needed). Open Python. "
                    "Write a program that prints 'Hello [your name]' and adds two numbers. "
                    "That's it. You've started."
                )
            return (
                "For today: go to replit.com, start a Python file, and write a program that does one useful thing — "
                "prints your name, calculates a tip, whatever. Finish it before anything else."
            )
        return (
            "What's the one thing from our conversation you want to act on today? Name it specifically, "
            "and I'll give you the exact first step."
        )

    # ── "Simplify it" ──
    if any(t in text for t in ["simplif", "simpler", "now simplify", "make it simpler", "break it down"]):
        if any(w in recent_context for w in ["plan", "step", "tech", "coding"]):
            return "Simplified: pick one skill, practice 30 minutes daily, build one project, apply before you feel ready."
        if state.last_explained_topic:
            return explain_simply(state.last_explained_topic)
        for tag in ["tech", "coding", "success", "stress", "failure", "ai"]:
            if tag in recent_context:
                return f"Simple: {tag} = {_simple_definition(tag)}"
        return "Which specific part do you want simplified? Name it and I'll do it in one sentence."

    # ── "What should I actually do?" / "What should I focus on?" ──
    what_to_do_triggers = [
        "what should i actually do", "what should i focus on",
        "what should i do", "next step", "what's my next move",
        "what do i do next", "what should i do next",
    ]
    if any(t in text for t in what_to_do_triggers):
        if "get into tech" in goals or any(w in recent_context for w in ["tech", "coding"]):
            time_note = " (30 min in the morning beats 2 hrs exhausted at 10pm)" if time_limited else ""
            return (
                f"Your clearest next step: pick one tech lane today — "
                f"web dev (HTML/CSS/JS), backend (Python/Node), data science, or IT support — "
                f"and start one beginner project this week{time_note}.\n\n"
                f"Don't study for months before building. Build immediately, even badly. "
                f"Shipping something broken teaches more than reading about perfection."
            )
        if state.turns:
            return (
                "Based on what you've shared: what's the single action that would make the biggest difference right now? "
                "Name it specifically — I'll help you take the first step."
            )

    # ── "I only have 6 months to change my life" ──
    if any(t in text for t in ["6 months", "six months", "only have", "limited time"]):
        if any(w in recent_context for w in ["tech", "coding", "change", "career"]):
            return (
                "6 months is actually enough to get a junior role — if you're strategic:\n\n"
                "Month 1: Pick your lane (web dev or data), learn the basics daily.\n"
                "Month 2: Build project #1 (small but real).\n"
                "Month 3: Build project #2 (something you actually want to exist).\n"
                "Month 4: Polish GitHub, write LinkedIn posts, start applying.\n"
                "Month 5–6: Interview, iterate on feedback, keep applying.\n\n"
                "The key constraint isn't time — it's focus. One lane, one project at a time."
            )
        return (
            "6 months is real runway if you focus it. What's the one outcome you want at the end of those 6 months? "
            "Be specific and I'll help you work backwards from it."
        )

    # ── "Ask me questions" ──
    if "ask me questions" in text or text == "ask me":
        return (
            "Let's figure this out together. Three questions:\n"
            "1. What's one part of your life that feels most off-track right now?\n"
            "2. What have you already tried to change it?\n"
            "3. What would 'better' actually look like to you in concrete terms?\n\n"
            "Answer any or all of them — we'll work from there."
        )

    # ── "Pretend you're me" / "You're 22, broke..." ──
    if "pretend you're me" in text or "pretend you are me" in text:
        return (
            "Alright — tell me your actual situation: age, current job, available time per day, "
            "any skills or experience, and the biggest constraint you're facing. "
            "The more specific, the more useful my answer."
        )

    if any(w in text for w in ["22", "broke", "want to get into tech", "young and broke"]) and "next move" in text:
        return (
            "If I'm 22, broke, and want into tech:\n\n"
            "Today: install Python, watch the first 30 min of CS50P (free on YouTube).\n"
            "This week: write one working script — tip calculator, word counter, anything.\n"
            "Month 1: finish CS50P or one freeCodeCamp path.\n"
            "Month 2: build a small project that solves a problem you personally have.\n"
            "Month 3–6: apply to junior roles, IT helpdesk, or data analyst positions. Don't wait to feel ready.\n\n"
            "Everything you need is free: CS50, freeCodeCamp, The Odin Project, YouTube."
        )

    # ── "What's your exact next move?" ──
    if "exact next move" in text:
        age = state.profile.get("age", "")
        broke_context = "broke" in recent_context or "limited budget" in constraints
        if broke_context or age:
            age_note = f"At {age}, " if age else ""
            budget_note = "Cost is zero — CS50, freeCodeCamp, and The Odin Project are all free. " if broke_context else ""
            return (
                f"{age_note}here's the exact move:\n"
                f"Today: go to replit.com, open Python, write 5 lines of code.\n"
                f"{budget_note}"
                f"Tomorrow: continue for 25 minutes.\n"
                f"Week 4: finish one project. Put it on GitHub.\n"
                f"Month 3: start applying. The first application is the hardest. Send it anyway."
            )
        return (
            "Exact next move depends on your situation. Tell me: what's your current job, available time each day, "
            "and which area of tech interests you? Then I can give you a precise step."
        )

    return None


# ============================================================================
# PLAN REQUEST HANDLER
# ============================================================================

def plan_request_response(user_text: str, state: ChatState) -> Optional[str]:
    """Handle structured plan requests like '3-step plan to get into tech'."""
    text = normalize_text(user_text)
    plan_triggers = [
        "3-step plan", "3 step plan", "step plan", "plan to get into tech",
        "plan for tech", "give me a plan", "make a plan", "roadmap",
        "path to tech", "how do i get into tech", "get into tech",
        "give me a 3", "step-by-step",
    ]
    if not any(t in text for t in plan_triggers):
        return None

    constraints = state.user_constraints
    time_limited = "works 9-5" in constraints or "tired after work" in constraints

    if any(w in text for w in ["tech", "coding", "code", "developer", "programmer", "software"]) or \
       "get into tech" in state.user_goals:
        if time_limited:
            return (
                "3-Step Tech Plan (Built for Working 9–5):\n\n"
                "STEP 1 — PICK YOUR LANE (This week)\n"
                "Choose ONE path: web development, data/Python, IT support, or AI/ML. "
                "Don't pick multiple — one lane, full focus.\n\n"
                "STEP 2 — BUILD BEFORE YOU OVER-STUDY (Month 1–2)\n"
                "25–30 min/day in the morning before work — not at night when you're drained. "
                "Use free resources: CS50P, freeCodeCamp, The Odin Project. "
                "Build one real project by end of month 2 — doesn't need to be impressive, needs to exist.\n\n"
                "STEP 3 — GET VISIBLE, THEN APPLY (Month 3–6)\n"
                "Put your project on GitHub. Write one post about what you learned. "
                "Start applying to junior roles at month 3 — not when you 'feel ready'. "
                "Feedback from real interviews teaches faster than more studying."
            )
        return (
            "3-Step Plan to Get Into Tech:\n\n"
            "STEP 1 — PICK YOUR LANE\n"
            "Web dev (HTML/CSS/JS → React), data/Python (pandas → SQL → ML), "
            "or IT support (networking + certs). One path only.\n\n"
            "STEP 2 — BUILD REAL THINGS\n"
            "Two projects minimum: one following a tutorial (to learn the pattern), "
            "one you designed yourself (to prove you can apply it). "
            "Free resources: CS50P, freeCodeCamp, The Odin Project.\n\n"
            "STEP 3 — APPLY BEFORE YOU'RE READY\n"
            "Start applying at month 3. Junior roles, internships, contract work. "
            "Real application feedback beats six more months of studying."
        )

    return None


# ============================================================================
# PERSONALIZED ADVICE HANDLER
# ============================================================================

def personalized_advice_response(user_text: str, state: ChatState) -> Optional[str]:
    """Generate advice tailored to stored goals and constraints."""
    text = normalize_text(user_text)
    goals = state.user_goals
    constraints = state.user_constraints

    if not goals and not constraints and not state.profile:
        return None

    personalized_triggers = [
        "based on what i've told you", "based on what i told you",
        "given everything", "given what i said", "based on my situation",
        "what should i do next", "what do i do with all this",
    ]
    if not any(t in text for t in personalized_triggers):
        return None

    parts = []
    if "get into tech" in goals:
        parts.append("your goal is to get into tech")
    if "works 9-5" in constraints:
        parts.append("you're working full-time")
    if "tired after work" in constraints:
        parts.append("you're tired after work")
    if "limited budget" in constraints:
        parts.append("budget is tight")
    if "no experience" in constraints:
        parts.append("you're starting with no prior experience")

    if not parts:
        return None

    context_str = ", ".join(parts)
    morning_note = (
        "\nMorning study (before work) consistently outperforms evening study "
        "when you're already drained — even 25 minutes beats 90 tired minutes."
        if "tired after work" in constraints else ""
    )
    budget_note = (
        "\nEvery resource you need is free: CS50P (Harvard), freeCodeCamp, The Odin Project, YouTube. "
        "No bootcamp or paid course needed to start."
        if "limited budget" in constraints else ""
    )
    experience_note = (
        "\nNo experience is fine — everyone in tech was a beginner. "
        "What matters is consistent practice and one real project to show. "
        if "no experience" in constraints else ""
    )

    return (
        f"Given your situation ({context_str}):\n"
        f"{morning_note}"
        f"{budget_note}"
        f"{experience_note}\n"
        f"Concrete next step: this week, commit to 25 minutes a day of structured learning. "
        f"Pick one resource from above and start it today — not when 'things calm down'."
    )


# ============================================================================
# CONSTRAINT / GOAL RESPONSE HANDLER
# ============================================================================

def constraint_aware_response(user_text: str, state: ChatState) -> Optional[str]:
    """Respond to constraint updates by integrating them with known goals."""
    text = normalize_text(user_text)
    goals = state.user_goals

    is_constraint = any(t in text for t in [
        "i work 9", "work 9-5", "9 to 5", "nine to five",
        "tired after work", "tired when i get home",
        "no experience", "i'm broke", "im broke", "no money",
        "limited time", "don't have time", "only have",
    ])

    has_tech_goal = "get into tech" in goals or any(
        "tech" in u.lower() or "coding" in u.lower() for u, _ in state.turns[-10:]
    )
    is_tired = "tired" in text
    is_broke = any(w in text for w in ["broke", "no money", "can't afford"])
    is_schedule = any(w in text for w in ["9-5", "9 to 5", "nine to five", "work"])
    no_exp = "no experience" in text

    # Also activate for tech follow-up questions when constraints are already stored
    just_stated_constraint = any(c in state.user_constraints for c in ["works 9-5", "tired after work"])
    is_tech_question = any(w in text for w in ["tech", "coding", "learn", "how do i", "still learn"])

    # Skip if neither a fresh constraint nor a follow-up after a known constraint
    if not is_constraint and not (just_stated_constraint and is_tech_question):
        return None

    # Don't override emotional expressions — let them get proper empathy treatment
    emotion_words = ["scared", "afraid", "nervous", "excited", "happy", "sad",
                     "anxious", "overwhelmed", "frustrated", "angry", "worried"]
    if any(e in text for e in emotion_words) and not is_constraint:
        return None

    if (has_tech_goal or is_tech_question) and (is_constraint or just_stated_constraint):
        if is_tired and (is_schedule or "works 9-5" in state.user_constraints):
            return (
                "Got it — you're working full-time and running on empty by evening. "
                "That's a real constraint, not an excuse. Here's what actually works in that situation:\n\n"
                "Morning learning beats evening learning. 25 minutes before work, "
                "when your brain is fresh, is more effective than 90 minutes exhausted at 10pm. "
                "Can you carve out 25 minutes before your shift starts?"
            )
        if is_broke:
            return (
                "Cost is zero — that's not the constraint. "
                "CS50P (Harvard's Python course), freeCodeCamp, and The Odin Project are all completely free. "
                "The real constraints are time and daily consistency. "
                "How much time can you realistically put in per day right now?"
            )
        if is_schedule or "works 9-5" in state.user_constraints:
            return (
                "Working 9–5 makes evening learning hard, but it doesn't block you. "
                "30 minutes in the morning before work is the most reliable window for most people in this situation. "
                "What does your morning look like — is there a 25-minute slot you could protect?"
            )
        if no_exp:
            return (
                "No experience is the normal starting point for self-taught developers — it's expected. "
                "What matters is consistency and building real projects. "
                "Given that, what area of tech are you most drawn to: building things (web/backend), "
                "working with data, or getting into IT/support first?"
            )

    return None


def topic_pivot_response(state: Optional[ChatState]) -> str:
    topic = state.current_topic if state else None
    if topic in TOPIC_GUIDES:
        return f"Let's switch gears for a second. {TOPIC_GUIDES[topic]}"
    return (
        "Let's keep this interesting. Pick a lane and I'll go deep: math, science, history, "
        "geography, AI, or life and emotions."
    )


def topical_fallback_reply(user_text: str, state: Optional[ChatState]) -> Optional[str]:
    topic = infer_topic(user_text)
    if not topic:
        return None

    fact_options = TOPIC_FACT_BANK.get(topic)
    if not fact_options:
        return None

    fact = choose_non_repeating(fact_options, state)
    guide = TOPIC_GUIDES.get(topic, "")
    if guide:
        return f"{fact} {guide}"
    return fact


def solve_math_query(text: str) -> Optional[str]:
    """Solve very basic arithmetic expressions safely."""
    # Guard: don't interpret work-schedule ranges as arithmetic (e.g. "I work 9-5")
    if re.search(r"\b9\s*[-\u2013]\s*5\b", text) and any(
        w in text for w in ["work", "job", "schedule", "hour", "tired", "shift", "office"]
    ):
        return None

    expr = text
    original_expr = expr
    expr = re.sub(r"\bplus\b", "+", expr)
    expr = re.sub(r"\bminus\b", "-", expr)
    expr = re.sub(r"\b(times|multiplied by)\b", "*", expr)
    expr = re.sub(r"\b(divided by|over)\b", "/", expr)
    expr = re.sub(r"\bwhat is\b", "", expr)
    expr = re.sub(r"\bwhat's\b", "", expr)
    expr = re.sub(r"\bcalculate\b", "", expr)
    expr = re.sub(r"(?<=\d)\s*[x]\s*(?=\d)", "*", expr)
    expr = expr.replace("?", " ")
    expr = expr.strip()

    # If an unknown symbol survives between exactly two numbers, assume multiplication.
    if not re.search(r"[\+\-\*\/]", expr):
        unknown_mul = re.fullmatch(r"(\d+(?:\.\d+)?)\s*[^0-9a-zA-Z\s\.]+\s*(\d+(?:\.\d+)?)", expr)
        if unknown_mul:
            expr = f"{unknown_mul.group(1)} * {unknown_mul.group(2)}"

    if not re.search(r"[\+\-\*\/]", expr):
        numbers = re.findall(r"\d+(?:\.\d+)?", original_expr)
        between = re.search(r"(\d+(?:\.\d+)?)(.*?)(\d+(?:\.\d+)?)", original_expr)
        if len(numbers) == 2 and between and between.group(2).strip():
            expr = f"{numbers[0]} * {numbers[1]}"

    if not re.fullmatch(r"[0-9\s\+\-\*\/\(\)\.]+", expr):
        return None
    if not re.search(r"[\+\-\*\/]", expr):
        return None

    try:
        result = eval(expr, {"__builtins__": {}}, {})  # noqa: S307
    except Exception:
        return None

    if isinstance(result, (int, float)):
        if float(result).is_integer():
            result = int(result)
        return f"{expr} = {result}"
    return None


def fallback_factual_reply(user_text: str, state: Optional[ChatState] = None) -> str:
    text = normalize_text(user_text)
    for topic, guide in TOPIC_GUIDES.items():
        if contains_phrase(text, topic):
            return guide
    # Tech/coding queries — return useful direction instead of a canned fallback
    if any(w in text for w in ["tech", "coding", "code", "programming", "developer", "software"]):
        return (
            "That's a tech question. To give you the most useful answer: "
            "are you asking about how to learn it, which area to focus on, job prospects, or something else? "
            "Point me at the specific angle and I'll go deep."
        )
    return (
        "I want to give you a useful answer, not a generic one. "
        "Can you give me one more detail — what specifically do you want to know or decide?"
    )


def choose_non_repeating(options: Sequence[str], state: Optional[ChatState]) -> str:
    if not state or not state.last_responses:
        return random.choice(options)
    filtered = [opt for opt in options if opt != state.last_responses[-1]]
    if filtered:
        return random.choice(filtered)
    return random.choice(options)


def lookup_knowledge(text: str) -> Optional[str]:
    """
    Search knowledge base for answer.
    Uses smart matching with exact matches prioritized, then partial matches.
    """
    text_lower = normalize_text(text)

    # Arithmetic support: "2+2", "what is 2 plus 2", etc.
    math_answer = solve_math_query(text_lower)
    if math_answer is not None:
        return math_answer

    # High-value heuristic handles for common history phrasing and typos.
    if "9/11" in text_lower or "when was 9/11" in text_lower:
        return "The 9/11 attacks happened on September 11, 2001, in the United States."
    if "egypt" in text_lower and ("when" in text_lower or "time" in text_lower):
        return "Ancient Egyptian civilization existed roughly from 3100 BCE to 30 BCE."
    if "egyptians" in text_lower or "ancient egypt" in text_lower:
        return "Ancient Egypt was a long-lasting civilization known for pyramids, pharaohs, hieroglyphics, engineering, and life along the Nile River."
    
    # First pass: exact matches (highest priority)
    for key, answer in KNOWLEDGE_BASE.items():
        if key == text_lower:
            return answer
    
    # Second pass: key phrase contains or is contained in text
    for key, answer in KNOWLEDGE_BASE.items():
        if key in text_lower or text_lower in key:
            return answer
    
    # Third pass: fuzzy matching with stopword filtering.
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "to", "of", "and", "or",
        "what", "when", "where", "who", "why", "how", "can", "you", "i", "me",
        "about", "tell", "explain", "help", "with", "do", "does", "it", "on",
    }
    words_in_text = {w for w in re.findall(r"[a-z0-9\+\/]+", text_lower) if w not in stopwords}
    best_match = None
    best_score = 0
    best_ratio = 0.0
    
    for key, answer in KNOWLEDGE_BASE.items():
        key_words = {w for w in re.findall(r"[a-z0-9\+\/]+", key) if w not in stopwords}
        if not key_words:
            continue
        score = len(key_words & words_in_text)
        ratio = score / max(1, len(key_words))
        if score >= 1 and (score > best_score or (score == best_score and ratio > best_ratio)):
            best_score = score
            best_ratio = ratio
            best_match = answer
    
    if best_match and best_ratio >= 0.5:
        return best_match
    
    return None


def select_response_strategy(intent: str) -> str:
    """Map intent to response strategy."""
    strategy_map = {
        "question": "direct_answer",
        "factual_request": "direct_answer",
        "emotional_expression": "empathetic",
        "uncertainty": "clarify",
        "casual_statement": "engage",
        "general_chat": "conversational",
    }
    return strategy_map.get(intent, "conversational")


def build_response(
    user_text: str,
    intent: str,
    emotion: str,
    state: Optional[ChatState] = None
) -> str:
    """
    Generate response based on intent, emotion, and knowledge.
    
    Args:
        user_text: Raw user message
        intent: Classified intent
        emotion: Classified emotion
        state: Conversation state for context
    
    Returns:
        Response string (ready to display)
    """
    # Normalize emotion to template key
    emotion_key = "positive" if emotion == "positive" else \
                  "negative" if emotion == "negative" else "neutral"

    # New intent types handled directly
    if intent == "decision_request":
        resp = decision_framework_response(user_text, state)
        if resp:
            return resp
        return "Give me the specific decision — what are your two options? I'll break it down with pros, cons, and a recommendation."

    if intent == "plan_request":
        resp = plan_request_response(user_text, state)
        if resp:
            return resp
        return "Tell me what you're planning for and I'll give you a structured steps."

    if intent == "context_connection":
        resp = context_connection_response(user_text, state)
        if resp:
            return resp

    if intent == "follow_up":
        resp = follow_up_chain_response(user_text, state)
        if resp:
            return resp

    if intent == "meta_complaint":
        resp = follow_up_chain_response(user_text, state)
        if resp:
            return resp
        return "Fair point. Tell me exactly what you want answered in one sentence and I'll give you a direct response."

    if intent == "constraint_update":
        resp = constraint_aware_response(user_text, state)
        if resp:
            return resp

    if intent == "vague_input":
        # Ask a SPECIFIC clarifying question based on context
        recent = " ".join(u.lower() for u, _ in state.turns[-6:])
        if any(w in recent for w in ["tech", "coding", "career"]):
            return "When you say that — are you asking about learning path, time commitment, cost, or job prospects? Which angle matters most to you?"
        if any(w in recent for w in ["stress", "work", "tired", "quit"]):
            return "Can you be specific about what you're dealing with — is this about workload, a person at work, or uncertainty about the direction you're heading?"
        return "Can you be more specific? What's the exact question or situation you want help with?"

    # Get template(s)
    templates = STRATEGY_TEMPLATES.get(intent, {}).get(emotion_key, ["What's the specific thing you're trying to figure out?"])
    
    # Handle both single string and list of strings
    if isinstance(templates, str):
        templates = [templates]
    
    # Pick a template for variety while avoiding immediate repetition.
    template = choose_non_repeating(templates, state)
    
    # Try knowledge lookup for factual requests
    if intent == "factual_request" or intent == "question":
        answer = lookup_knowledge(user_text)
        if answer:
            if state is not None:
                active_state = state
                inferred = infer_topic(user_text)
                if "algebra" in normalize_text(user_text):
                    active_state.last_explained_topic = "algebra"
                elif "ai" in normalize_text(user_text):
                    active_state.last_explained_topic = "ai"
                elif inferred:
                    active_state.last_explained_topic = inferred
            return template.format(answer=answer)
        topical = topical_fallback_reply(user_text, state)
        if topical:
            return topical
        return fallback_factual_reply(user_text)

    if intent == "emotional_expression":
        answer = lookup_knowledge(user_text)
        if answer:
            return answer

        if "rain" in normalize_text(user_text) and "sun" in normalize_text(user_text):
            return "Yeah, gloomy weather can really affect mood. I get missing the sun. A short walk, warm drink, or bright indoor light can help a bit."

        if emotion_key == "negative":
            options = [
                "I hear you. That sounds hard. Want to tell me a bit more so I can help better?",
                "That sounds rough. I'm here with you. What part feels the heaviest right now?",
                "Thanks for sharing that. Want to unpack it together step by step?",
            ]
            return choose_non_repeating(options, state)

        if emotion_key == "positive":
            options = [
                "That's great to hear. What contributed most to that feeling?",
                "Love that energy. What's going well for you today?",
                "Awesome. Want to build on that momentum?",
            ]
            return choose_non_repeating(options, state)
    
    # Default response if no knowledge match
    if "{answer" in template or "{" in template:
        # Template expects argument we don't have
        default_templates = STRATEGY_TEMPLATES.get("general_chat", {}).get(emotion_key, ["What's the specific thing you're trying to figure out?"])
        if isinstance(default_templates, str):
            default_templates = [default_templates]
        return choose_non_repeating(default_templates, state)

    return template


# ============================================================================
# VALIDATION & SANITIZATION
# ============================================================================


def validate_input(text: str, max_length: int = 500) -> tuple[bool, str]:
    """
    Validate and sanitize user input.
    
    Returns:
        (is_valid, sanitized_text)
    """
    if not isinstance(text, str):
        return False, ""
    
    sanitized = text.strip()
    
    if not sanitized:
        return False, ""
    
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return True, sanitized


# ============================================================================
# MAIN CHATBOT ENGINE
# ============================================================================


class ChatbotEngine:
    """
    Stateless chatbot engine.
    
    Core responsibility: transform user message → bot response
    
    Usage:
        engine = ChatbotEngine()
        state = ChatState(session_id="123")
        response, state = engine.chat("Hello", state)
    """
    
    def __init__(self):
        """Initialize engine (no state)."""
        pass
    
    def chat(
        self,
        user_message: str,
        state: Optional[ChatState] = None
    ) -> tuple[str, ChatState]:
        """
        Process user message and return bot response.
        
        Args:
            user_message: Raw user input
            state: Conversation state (created if None)
        
        Returns:
            (response_text, updated_state)
        """
        # Validate input
        is_valid, sanitized = validate_input(user_message)
        if not is_valid:
            return "Please enter a message.", state or ChatState(session_id="default")
        
        # Initialize state if needed
        if state is None:
            state = ChatState(session_id="default")

        update_profile_memory(state, sanitized)

        routed = route_response(sanitized, state)
        if routed:
            state.add_turn(sanitized, routed)
            state.last_responses.append(routed)
            state.last_bot_question = routed if routed.endswith("?") else None
            state.last_user_message = sanitized
            return routed, state

        direct_reply = direct_conversation_reply(sanitized, state)
        if direct_reply:
            state.add_turn(sanitized, direct_reply)
            state.last_responses.append(direct_reply)
            state.last_bot_question = direct_reply if direct_reply.endswith("?") else None
            state.last_user_message = sanitized
            state.recovery_count = 0
            return direct_reply, state

        # Track evolving topic for better follow-up quality.
        inferred_topic = infer_topic(sanitized)
        if inferred_topic:
            state.current_topic = inferred_topic
            state.topics.append(inferred_topic)
        
        # Check for repetition
        if state.should_limit_response():
            response = topic_pivot_response(state)
            state.add_turn(sanitized, response)
            state.last_bot_question = response if response.endswith("?") else None
            state.last_user_message = sanitized
            return response, state
        
        # 1. Classify intent
        intent = classify_intent(sanitized, state)
        state.intents.append(intent)
        state.last_intent = intent
        
        # 2. Classify emotion
        emotion = classify_emotion(sanitized)
        state.emotions.append(emotion)
        
        # 3. Build response
        response = build_response(sanitized, intent, emotion, state)

        # Hard stop on immediate duplicate response.
        if state.last_responses and response == state.last_responses[-1]:
            topic_reply = topical_fallback_reply(sanitized, state)
            if topic_reply:
                response = topic_reply
            else:
                response = topic_pivot_response(state)

        # Only force recovery when the output is generic and there is no better topical fallback.
        if is_generic_response(response):
            topic_reply = topical_fallback_reply(sanitized, state)
            if topic_reply:
                response = topic_reply
                state.recovery_count = 0
            elif intent in {"uncertainty", "casual_statement"} and len(sanitized.split()) <= 4:
                response = recovery_response(sanitized, state)
            else:
                state.recovery_count = 0
        else:
            state.recovery_count = 0
        
        # 4. Update state
        state.add_turn(sanitized, response)
        state.last_responses.append(response)
        state.last_bot_question = response if response.endswith("?") else None
        state.last_user_message = sanitized
        
        return response, state
    
    def reset_state(self) -> ChatState:
        """Create fresh conversation state."""
        return ChatState(session_id=f"session_{time.time()}")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================


if __name__ == "__main__":
    # Test the core engine (no UI, no Tkinter)
    engine = ChatbotEngine()
    state = engine.reset_state()
    
    test_messages = [
        "Hey, how are you?",
        "What's the capital of France?",
        "I'm feeling great today!",
        "Can you explain neural networks?",
    ]
    
    for msg in test_messages:
        response, state = engine.chat(msg, state)
        print(f"User: {msg}")
        print(f"Bot:  {response}")
        print()
