import json
import time
import google.generativeai as genai
from config import settings
from utils.logger import log_agent_execution

class BaseAgent:
    def __init__(self, name: str, system_instruction: str):
        self.name = name
        self.system_instruction = system_instruction
        
        # Configure Gemini API
        if settings.GOOGLE_API_KEY:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            # Use gemini-2.5-flash-lite as the primary fast and accurate model
            self.model = genai.GenerativeModel(
                model_name="gemini-2.5-flash-lite",
                system_instruction=system_instruction
            )
        else:
            raise ValueError("GOOGLE_API_KEY not configured. Please supply a valid Google API Key.")

    def run_llm(self, prompt: str, enforce_json: bool = True) -> dict:
        """Executes the prompt against Gemini, handles logging, and parses JSON output if requested"""
        start_time = time.time()
        inputs = {"prompt": prompt}
        
        generation_config = {}
        if enforce_json:
            generation_config["response_mime_type"] = "application/json"
            
        try:
            # Generate content
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            text_response = response.text.strip()
            
            # Parse output
            if enforce_json:
                try:
                    # Clean up markdown code block wrappers if Gemini still includes them despite MIME type
                    if text_response.startswith("```json"):
                        text_response = text_response.split("```json", 1)[1].rsplit("```", 1)[0].strip()
                    elif text_response.startswith("```"):
                        text_response = text_response.split("```", 1)[1].rsplit("```", 1)[0].strip()
                        
                    parsed_output = json.loads(text_response)
                except Exception as json_err:
                    parsed_output = {
                        "error": "Failed to parse JSON response from LLM",
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
