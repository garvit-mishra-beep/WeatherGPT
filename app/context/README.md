# Context Management Layer (`app/context/`)

## 1. Purpose
Manages conversational state, multi-turn dialogue history, location/temporal inheritance, and sliding-window context trimming across sessions.

## 2. Responsibilities
- Track active sessions and manage turn-by-turn question/answer history.
- Propagate geographic location and temporal windows across follow-up queries unless explicitly overridden.
- Trim conversation history using a sliding window (`max_history_turns=10`) while never dropping the current user prompt.
- Protect against prompt injection attacks by maintaining strict message role segregation.

## 3. Important Files
- `manager.py`: `ContextManager` coordinating session lifecycles, turn recording, and request preparation.
- `builder.py`: `ContextBuilder` converting sessions and normalized requests into validated `BrainRequest` payloads.
- `policy.py`: `ContextPolicy` enforcing context retention limits and trimming rules.
- `models.py`: `SessionContext` and `ConversationTurn` Pydantic models.

## 4. Invariants
- Dynamic switching: Users can seamlessly move between Brain domains (e.g. General $\to$ Farmer $\to$ Researcher) across turns without permanent session lock.
- Clean isolation: Conversation history is structured as typed turns and cannot be manipulated to inject system instructions.
