from agents.base import BaseAgent
from prompts.templates import INTENT_SYSTEM

class IntentClassificationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="IntentClassificationAgent",
            system_instruction=INTENT_SYSTEM
        )

    def process(self, cleaned_body: str) -> dict:
        prompt = f"Identify intents for this email body:\n{cleaned_body}"
        return self.run_llm(prompt, enforce_json=True)
