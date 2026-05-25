from agents.base import BaseAgent
from prompts.templates import EXTRACTION_SYSTEM

class EntityExtractionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="EntityExtractionAgent",
            system_instruction=EXTRACTION_SYSTEM
        )

    def process(self, cleaned_body: str) -> dict:
        prompt = f"Extract entities from this customer email body:\n{cleaned_body}"
        return self.run_llm(prompt, enforce_json=True)
