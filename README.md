# ARC Chatbot

ARC is a modular, interview-ready chatbot project built in Python. It demonstrates a complete conversational pipeline: intent detection, memory, knowledge lookup, response strategy, personality modulation, confidence scoring, and proactive prompts. The system is intentionally lightweight (regex and rules) so the full logic is transparent and easy to explain.

## Features

- Intent detection with regex-based patterns
- Emotion detection and tone adaptation
- Multi-turn memory and topic tracking
- Knowledge and reasoning engine (facts + math)
- Response strategy selection with loop prevention
- Personality engine with persistence across turns
- Confidence metrics with exponential decay
- Proactive prompts when conversation stalls
- Teaching system with multi-level explanations
- CLI chat loop (easy to test and demo)

## Project Structure

- arc.py: All chatbot logic and the main loop

## Requirements

- Python 3.8+

## Quick Start

1. Open a terminal in the project folder
2. Run the chatbot:

```bash
python arc.py
```

3. Type your message and press Enter
4. Type "exit" to quit

## How the Pipeline Works

ARC processes each message in a consistent order:

1. Detect emotion
2. Detect intent
3. Build context from memory
4. Select response strategy
5. Generate response using knowledge/memory
6. Adapt tone and personality
7. Update memory
8. Return the response

This makes the code easy to walk through and explain in interviews.

## Notes

- The project is deliberately rule-based (no external NLP libraries) so the behavior is deterministic and easy to reason about.
- Personality and learning systems are designed for clarity over complexity.

## License

MIT
