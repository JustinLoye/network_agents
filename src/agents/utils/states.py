from typing import Annotated
from typing_extensions import TypedDict
import copy
import re
from langchain_core.messages import BaseMessage
from langchain_core.messages import AnyMessage, AIMessage
from langgraph.graph.message import add_messages
from langgraph.managed.is_last_step import IsLastStep, RemainingSteps


def serialize_state(state):
    def serialize_value(value):
        if isinstance(value, BaseMessage):
            return {"type": value.type, "content": value.content}
        elif isinstance(value, list):
            return [serialize_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: serialize_value(v) for k, v in value.items()}
        else:
            return value

    return serialize_value(state)


def remove_thoughts(content: str) -> str:
    """Remove <think>...</think> tags from content"""
    return re.sub(r"<think>.*?</think>\s*", "", content, flags=re.DOTALL)


def extract_thoughts(content: str) -> str:
    """Extract content from <think>...</think> tags"""
    matches = re.findall(r"<think>(.*?)</think>", content, flags=re.DOTALL)
    return "\n".join(matches) if matches else ""


def add_clean_messages(
    left: list[AnyMessage], right: list[AnyMessage]
) -> list[AnyMessage]:
    """Add messages with thinking content removed"""
    if isinstance(right, dict) and "messages" in right:
        right_copy = right["messages"]
    else:
        right_copy = copy.deepcopy(right)
    cleaned_right = []
    for msg in right_copy:
        if isinstance(msg, AIMessage) and msg.content:
            cleaned_msg = msg.model_copy(deep=True)
            cleaned_msg.content = remove_thoughts(str(msg.content))
            cleaned_right.append(cleaned_msg)
        # Tool message and others
        else:
            cleaned_right.append(msg)

    return add_messages(left, cleaned_right)


def add_thoughts_only(
    left: list[AnyMessage], right: list[AnyMessage]
) -> list[AnyMessage]:
    """Extract only the thinking content as messages"""
    if isinstance(right, dict) and "thoughts" in right:
        right_copy = right["thoughts"]
    else:
        right_copy = copy.deepcopy(right)
    thought_messages = []
    for msg in right_copy:
        if isinstance(msg, AIMessage) and msg.content:
            thought_content = extract_thoughts(str(msg.content))
            if thought_content:
                thought_msg = AIMessage(content=str(msg.content))
                thought_messages.append(thought_msg)
    
    return add_messages(left, thought_messages)


class SplitThinkingAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_clean_messages]
    thoughts: Annotated[list[AnyMessage], add_thoughts_only]
    is_last_step: IsLastStep
    remaining_steps: RemainingSteps
