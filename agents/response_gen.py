from agents.base import BaseAgent
from prompts.templates import RESPONSE_SYSTEM

class ResponseGenerationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="ResponseGenerationAgent",
            system_instruction=RESPONSE_SYSTEM
        )

    def process(self, original_subject: str, original_body: str, sentiment: str, 
                entities: dict, validation_results: dict, api_responses: dict) -> dict:
        prompt = f"""
Original Email Subject: {original_subject}
Original Email Body:
{original_body}

Sentiment: {sentiment}
Extracted Entities: {entities}
Validation Results: {validation_results}
Core Banking API Outputs: {api_responses}

Draft a highly professional, secure customer response email addressing all scenarios. Keep security in mind by masking card numbers (e.g. XXXX-XXXX-XXXX-8901) and account numbers (XXXX7890) in the draft text.
"""
        return self.run_llm(prompt, enforce_json=True)
