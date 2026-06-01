import json
import time
import httpx
from config import settings
from utils.logger import log_agent_execution

class BaseAgent:
    def __init__(self, name: str, system_instruction: str):
        """Initializes the Agent with systemic instructions and maps Ollama endpoint config"""
        self.name = name
        self.system_instruction = system_instruction
        self.model_name = settings.OLLAMA_MODEL
        self.api_url = settings.OLLAMA_API_URL

    def run_llm(self, prompt: str, enforce_json: bool = True) -> dict:
        """Executes the prompt against local Ollama, handles logging, and parses JSON output if requested"""
        start_time = time.time()
        inputs = {"prompt": prompt}
        
        # Prepare the standard chat completion payload for Ollama
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": self.system_instruction},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
        
        # Enforce structured JSON formatting directly at the LLM level
        if enforce_json:
            payload["format"] = "json"
            
        try:
            # Send sync POST request to local Ollama chat endpoint
            with httpx.Client(timeout=None) as client:
                response = client.post(self.api_url, json=payload)
                response.raise_for_status()
                res_data = response.json()
                
            # Extract content from the chat response structure
            text_response = res_data["message"]["content"].strip()
            
            # Parse output
            if enforce_json:
                try:
                    # Strip markdown blocks if returned
                    if text_response.startswith("```json"):
                        text_response = text_response.split("```json", 1)[1].rsplit("```", 1)[0].strip()
                    elif text_response.startswith("```"):
                        text_response = text_response.split("```", 1)[1].rsplit("```", 1)[0].strip()
                        
                    parsed_output = json.loads(text_response)
                except Exception as json_err:
                    parsed_output = {
                        "error": "Failed to parse JSON response from Ollama",
                        "raw_response": text_response,
                        "exception": str(json_err)
                    }
            else:
                parsed_output = {"response": text_response}
                
            duration = int((time.time() - start_time) * 1000)
            parsed_output["agent_duration_ms"] = duration
            
            # Log successful agent execution
            log_agent_execution(self.name, "SUCCESS", inputs, parsed_output)
            return parsed_output
            
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            error_output = {
                "error": "LLM API Failure",
                "exception": str(e),
                "agent_duration_ms": duration
            }
            log_agent_execution(self.name, "FAILED", inputs, error_output)
            return error_output
