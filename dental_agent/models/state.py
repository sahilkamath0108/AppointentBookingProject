from typing import TypedDict, Annotated, Literal, Optional, List
from langchain_core.messages import BaseMessage
import operator

IntentLabel = Literal[
    "get_info",
    "book",
    "cancel",
    "reschedule",
    "unknown",
    "end",
]

AgentRoute = Literal[
    "info_agent",
    "booking_agent",
    "cancellation_agent",
    "rescheduling_agent",
    "end",
]


class SessionState(TypedDict):
    # Conversation history appended by nodes
    messages: Annotated[List[BaseMessage], operator.add]

    # Router output
    intent: Optional[IntentLabel]
    next_agent: Optional[AgentRoute]

    # Appointment fields extracted from conversation
    patient_id: Optional[str]
    requested_specialization: Optional[str]
    requested_doctor: Optional[str]
    requested_date_slot: Optional[str]
    current_date_slot: Optional[str]
    new_date_slot: Optional[str]

    # Tool results
    available_slots: Optional[List[dict]]
    operation_success: Optional[bool]
    operation_message: Optional[str]

    # Final text returned to CLI
    final_response: Optional[str]
