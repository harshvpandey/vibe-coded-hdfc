from agents.base import BaseAgent
from prompts.templates import UNDERSTANDING_SYSTEM

class EmailUnderstandingAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="EmailUnderstandingAgent",
            system_instruction=UNDERSTANDING_SYSTEM
        )

    def process(self, sender: str, subject: str, body: str) -> dict:
        prompt = f"Sender: {sender}\nSubject: {subject}\nBody:\n{body}"
        return self.run_llm(prompt, enforce_json=True)
