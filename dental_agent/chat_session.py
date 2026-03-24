from typing import List, Tuple

from langchain_core.messages import AIMessageChunk, BaseMessage, HumanMessage

from dental_agent.agent import dental_graph


def run_chat_turn(
    message_history: List[BaseMessage], user_text: str, recursion_limit: int = 20
) -> Tuple[str, List[BaseMessage]]:
    """
    Execute one assistant turn and return rendered text + updated message history.
    """
    working_history = list(message_history)
    working_history.append(HumanMessage(content=user_text))

    response_parts: List[str] = []
    final_messages = None

    for event_type, data in dental_graph.stream(
        {"messages": working_history},
        stream_mode=["messages", "values"],
        config={"recursion_limit": recursion_limit},
    ):
        if event_type == "messages":
            chunk, _meta = data
            if (
                isinstance(chunk, AIMessageChunk)
                and chunk.content
                and not getattr(chunk, "tool_calls", None)
            ):
                response_parts.append(chunk.content)
        elif event_type == "values":
            final_messages = data.get("messages", [])

    assistant_text = "".join(response_parts).strip()
    if not assistant_text and final_messages:
        last_message = final_messages[-1]
        assistant_text = str(getattr(last_message, "content", "")).strip()

    return assistant_text, (final_messages or working_history)
