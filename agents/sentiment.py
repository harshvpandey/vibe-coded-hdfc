from agents.base import BaseAgent
from prompts.templates import SENTIMENT_SYSTEM

class SentimentAnalysisAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="SentimentAnalysisAgent",
            system_instruction=SENTIMENT_SYSTEM
        )

    def process(self, cleaned_body: str) -> dict:
        prompt = f"Analyze customer sentiment and urgency for this email:\n{cleaned_body}"
        return self.run_llm(prompt, enforce_json=True)
