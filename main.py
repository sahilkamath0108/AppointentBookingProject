"""
Dental Scheduling Console
"""

from dotenv import load_dotenv
load_dotenv()

from dental_agent.chat_session import run_chat_turn

BANNER = """
╔══════════════════════════════════════════════════════════╗
║                Dental Scheduling Console                 ║
║                 LangGraph + Grok-4 (xAI)                ║
╚══════════════════════════════════════════════════════════╝
Sample queries:
  • Show available slots for an orthodontist
  • Book patient 1000082 with Emily Johnson on 5/10/2026 9:00
  • Cancel appointment for patient 1000082 at 5/10/2026 9:00
  • Reschedule patient 1000082 from 5/10/2026 9:00 to 5/12/2026 10:00
  • What appointments does patient 1000048 have?

Type 'quit' to exit.
"""


def run():
    print(BANNER)
    conversation_history = []

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "bye"}:
            print("Goodbye!")
            break

        print("\nAgent: ", end="", flush=True)

        try:
            response_text, updated_history = run_chat_turn(conversation_history, user_input)
        except Exception as exc:
            print(f"\nError: {exc}")
            continue

        print(response_text)
        conversation_history = updated_history


if __name__ == "__main__":
    run()
