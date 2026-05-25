from agents.base import BaseAgent
from prompts.templates import API_SELECTION_SYSTEM

class APISelectionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="APISelectionAgent",
            system_instruction=API_SELECTION_SYSTEM
        )

    def process(self, intents: list, entities: dict, validation_results: dict) -> dict:
        prompt = f"""
Intents: {intents}
Extracted Entities: {entities}
Validation Results: {validation_results}

Determine which backend core banking APIs are required to fulfill the requests.
Remember:
- Only select an API if the corresponding entity (account or card) has been successfully validated ("VALID").
- If validation failed, DO NOT select the data API for that resource.
"""
        return self.run_llm(prompt, enforce_json=True)
