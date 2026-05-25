from agents.base import BaseAgent
from prompts.templates import AUDIT_SYSTEM

class AuditorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="AuditorAgent",
            system_instruction=AUDIT_SYSTEM
        )

    def process(self, execution_trace: list) -> dict:
        prompt = f"Review this step-by-step orchestrator execution trace and generate the final audit report:\n{execution_trace}"
        return self.run_llm(prompt, enforce_json=True)
