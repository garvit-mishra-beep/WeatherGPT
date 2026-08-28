"""Context trimming and retention policies for multi-turn conversations."""

from typing import List
from pydantic import BaseModel, ConfigDict, Field

from app.context.models import ConversationTurn


class ContextPolicy(BaseModel):
    """Configuration for conversation history sliding window and budget."""
    max_history_turns: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum previous turns included in contextual prompts",
    )
    max_history_chars: int = Field(
        default=8000,
        ge=500,
        le=50000,
        description="Maximum character budget across conversation history",
    )
    preserve_initial_user_context: bool = Field(
        default=True,
        description="Whether to preserve critical entities from earlier turns",
    )

    model_config = ConfigDict(frozen=True)


def trim_conversation_turns(
    turns: List[ConversationTurn],
    policy: ContextPolicy,
) -> List[ConversationTurn]:
    """Trim conversation turns according to the configured ContextPolicy.

    Retains the most recent turns up to max_history_turns, ensuring total character length
    remains within safe LLM prompt bounds.

    Args:
        turns: Ordered list of ConversationTurn objects.
        policy: Configured ContextPolicy rules.

    Returns:
        List[ConversationTurn]: Trimmed slice of conversation turns.
    """
    if not turns:
        return []

    # 1. Apply maximum turns limit (take latest N turns)
    recent_turns = turns[-policy.max_history_turns:]

    # 2. Check total character budget
    total_chars = sum(len(t.content) for t in recent_turns)
    if total_chars <= policy.max_history_chars:
        return recent_turns

    # 3. Truncate older turns from the front of the window if character budget is exceeded
    trimmed: List[ConversationTurn] = []
    current_chars = 0
    for turn in reversed(recent_turns):
        turn_len = len(turn.content)
        if current_chars + turn_len > policy.max_history_chars and trimmed:
            break
        trimmed.insert(0, turn)
        current_chars += turn_len

    return trimmed
