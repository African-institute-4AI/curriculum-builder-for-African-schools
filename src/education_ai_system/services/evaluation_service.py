from langchain_groq import ChatGroq  # Changed from langchain_openai
from src.education_ai_system.tools.pinecone_exa_tools import PineconeRetrievalTool
from src.education_ai_system.utils.validators import load_prompt
from src.education_ai_system.utils.supabase_manager import SupabaseManager
import json
import re
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain_core.pydantic_v1 import ValidationError
from pydantic import BaseModel, Field, confloat, conint
from typing import Dict

# Define nested models
class MetricScore(BaseModel):
    score: conint(ge=0, le=5) = Field(..., description="Score from 0 to 5")
    reason: str = Field(..., description="Explanation for the score")

class AccuracyMetrics(BaseModel):
    curriculum_compliance: MetricScore
    topic_relevance: MetricScore
    content_consistency: MetricScore
    quality_readability: MetricScore
    cultural_relevance: MetricScore

class EvaluationResult(BaseModel):
    accuracy: AccuracyMetrics
    bias: MetricScore
    overall_accuracy: confloat(ge=0, le=5)

class ContentEvaluator:
    def __init__(self):
        # Replace OpenAI with Groq API
        self.llm = ChatGroq(
            temperature=0.1,
            model_name="llama3-70b-8192",  # Using the best available Groq model
            max_tokens=4096
        )
        self.retriever = PineconeRetrievalTool()

        # Initialize parser with our model
        self.parser = PydanticOutputParser(pydantic_object=EvaluationResult)
        
        # Load and modify prompt template
        self.prompt_template = self._create_prompt_template()

    def _create_prompt_template(self):
        # Load base prompt
        base_template = load_prompt("evaluation")
        
        # Create new template with format instructions
        return PromptTemplate(
            template=base_template + "\n{format_instructions}",
            input_variables=[
                "content_type", 
                "subject", 
                "grade_level", 
                "topic",
                "curriculum",
                "content"
            ],
            partial_variables={
                "format_instructions": self.parser.get_format_instructions()
            }
        )

    # evaluation_service.py
    def evaluate_content_by_context(self, content_type: str, context_id: str) -> dict:
        print(f"\n=== STARTING EVALUATION FOR {content_type.upper()} ===")
        print(f"Context ID: {context_id}")
        
        try:
            supabase = SupabaseManager()
            
            # Retrieve context
            print("Fetching context from database...")
            context_data = supabase.get_context_by_id(context_id)
            if not context_data:
                print("❌ ERROR: Context not found in database")
                return {"status": "error", "message": "Context not found"}
            print("✅ Context retrieved successfully")
            print(f"Context subject: {context_data.get('subject')}")
            print(f"Context grade: {context_data.get('grade_level')}")
            print(f"Context topic: {context_data.get('topic')}")
            
            # Retrieve content using context ID
            print(f"Fetching {content_type} content using context ID...")
            if content_type == "scheme_of_work":
                content_data = supabase.get_scheme_by_context(context_id)
            elif content_type == "lesson_plan":
                content_data = supabase.get_lesson_plan_by_context(context_id)
            elif content_type == "lesson_notes":
                content_data = supabase.get_lesson_notes_by_context(context_id)
            else:
                print("❌ ERROR: Invalid content type specified")
                return {"status": "error", "message": "Invalid content type"}
            
            if not content_data:
                print("❌ ERROR: Content not found for given context")
                return {"status": "error", "message": "Content not found for given context"}
            print("✅ Content retrieved successfully")
            print(f"Content ID: {content_data.get('id')}")
            
            # Prepare evaluation input data
            print("Building evaluation input...")
            input_data = {
                "content_type": content_type,
                "subject": context_data["subject"],
                "grade_level": context_data["grade_level"],
                "topic": context_data["topic"],
                "curriculum": context_data["context"],
                "content": content_data["content"]
            }
            
            # Format prompt with structured instructions
            prompt = self.prompt_template.format_prompt(**input_data)
            formatted_prompt = prompt.to_string()
            
            # Log the full prompt for debugging
            print("\n===== FULL EVALUATION PROMPT =====")
            print(formatted_prompt)
            print("===== END PROMPT =====\n")
            
            # Write prompt to file
            with open("evaluation_prompt_debug.txt", "w") as f:
                f.write(formatted_prompt)
            
            print("Sending prompt to LLM for evaluation...")
            
            try:
                response = self.llm.invoke(formatted_prompt)
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"LLM invocation failed: {str(e)}",
                    "context_id": context_id
                }
            
            if not response or not response.content:
                return {
                    "status": "error",
                    "message": "Empty response from LLM",
                    "context_id": context_id
                }
            
            print("✅ Received LLM response")
            
            # Log the full response
            print("\n===== FULL LLM RESPONSE =====")
            print(response.content)
            print("===== END RESPONSE =====\n")
            
            # Write full response to file for debugging
            with open("llm_response_debug.txt", "w") as f:
                f.write(response.content)
            
            print("Parsing evaluation response with Pydantic...")
            
            try:
                # Parse using Pydantic model
                evaluation_data = self.parser.parse(response.content)
                print("✅ Successfully parsed evaluation response")
                
                # Convert to dict for serialization
                result = evaluation_data.dict()
                result["status"] = "success"
                return result
                
            except ValidationError as e:
                print(f"❌ Pydantic validation failed: {str(e)}")
                return {
                    "status": "error",
                    "message": "Failed to validate evaluation structure",
                    "errors": str(e),
                    "raw_response": response.content[:1000] + "..." if len(response.content) > 1000 else response.content
                }
                
        except Exception as e:
            print(f"❌ CRITICAL ERROR: {str(e)}")
            return {"status": "error", "message": f"Evaluation failed: {str(e)}"}

    def _build_evaluation_prompt(self, payload) -> str:
        """Build prompt from template with dynamic values"""
        # Add explicit instructions to output only JSON
        json_instruction = (
            "\n\nIMPORTANT: OUTPUT MUST BE VALID JSON ONLY! "
            "DO NOT INCLUDE ANY OTHER TEXT BEFORE OR AFTER THE JSON OBJECT. "
            "USE THIS EXACT STRUCTURE:\n"
            '{"accuracy": {"curriculum_compliance": {"score": 0, "reason": ""}, '
            '"topic_relevance": {"score": 0, "reason": ""}, '
            '"content_consistency": {"score": 0, "reason": ""}, '
            '"quality_readability": {"score": 0, "reason": ""}, '
            '"cultural_relevance": {"score": 0, "reason": ""}}, '
            '"bias": {"score": 0, "reason": ""}}'
        )
        
        base_prompt = self.prompt_template.format(
            content_type=payload['content_type'],
            subject=payload['subject'],
            grade_level=payload['grade_level'],
            topic=payload['topic'],
            curriculum=payload['context'],
            content=payload['content']
        )
        
        return base_prompt + json_instruction

    def _parse_evaluation(self, response: str) -> dict:
        """Robustly extract JSON evaluation from LLM response without hardcoding"""
        try:
            # Attempt 1: Direct JSON parsing
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                pass
            
            # Attempt 2: Extract JSON from code block
            try:
                json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(1))
            except:
                pass
            
            # Attempt 3: Extract any JSON-like structure
            try:
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    # Clean common JSON issues
                    json_str = json_match.group(0)
                    json_str = re.sub(r',\s*\n\s*}', '}', json_str)  # Trailing commas
                    json_str = re.sub(r'[\x00-\x1f]', '', json_str)  # Control characters
                    return json.loads(json_str)
            except:
                pass
            
            # Attempt 4: Flexible score extraction (no hardcoded keys)
            try:
                # Extract all score-reason pairs
                score_reason_pairs = re.findall(
                    r'"([\w\s]+)":\s*{\s*"score":\s*(\d),\s*"reason":\s*"([^"]+)"', 
                    response,
                    re.IGNORECASE
                )
                
                if score_reason_pairs:
                    result = {"accuracy": {}, "bias": {}}
                    
                    for name, score, reason in score_reason_pairs:
                        name_clean = name.lower().replace(' ', '_').strip()
                        score_val = int(score)
                        
                        # Organize by category
                        if 'bias' in name_clean:
                            result["bias"] = {"score": score_val, "reason": reason}
                        else:
                            result["accuracy"][name_clean] = {
                                "score": score_val, 
                                "reason": reason
                            }
                    
                    # Calculate overall accuracy if possible
                    if result["accuracy"]:
                        scores = [v["score"] for v in result["accuracy"].values()]
                        result["overall_accuracy"] = sum(scores) / len(scores)
                    
                    return result
            except:
                pass
            
            # Final fallback: Return error with response snippet
            return {
                "status": "error",
                "message": "Could not parse evaluation response",
                "response_sample": response[:500] + "..." if len(response) > 500 else response
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Parse error: {str(e)}",
                "response_sample": response[:500] + "..." if len(response) > 500 else response
            }

    # ADD THIS NEW HELPER METHOD TO THE CLASS
    def _extract_json(self, response: str) -> dict:
        """Robust JSON extraction from LLM response with multiple fallback strategies"""
        
        # Attempt 1: Direct JSON parsing
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Attempt 2: Extract JSON from code block
        try:
            json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
        except:
            pass
        
        # Attempt 3: Extract any JSON-like structure
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                # Clean common JSON issues
                json_str = json_match.group(0)
                json_str = re.sub(r',\s*\n\s*}', '}', json_str)  # Fix trailing commas
                json_str = re.sub(r'[\x00-\x1f]', '', json_str)  # Remove control chars
                return json.loads(json_str)
        except:
            pass
        
        # Attempt 4: Flexible score extraction (no hardcoded keys)
        try:
            # Extract all score-reason pairs
            score_reason_pairs = re.findall(
                r'"([\w\s]+)":\s*{\s*"score":\s*(\d),\s*"reason":\s*"([^"]+)"', 
                response,
                re.IGNORECASE
            )
            
            if score_reason_pairs:
                result = {"accuracy": {}, "bias": {"score": 0, "reason": "Not evaluated"}}
                
                for name, score, reason in score_reason_pairs:
                    name_clean = name.lower().replace(' ', '_').strip()
                    score_val = int(score)
                    
                    # Organize by category
                    if 'bias' in name_clean:
                        result["bias"] = {"score": score_val, "reason": reason}
                    else:
                        result["accuracy"][name_clean] = {
                            "score": score_val, 
                            "reason": reason
                        }
                
                # Calculate overall accuracy if possible
                if result["accuracy"]:
                    scores = [v["score"] for v in result["accuracy"].values()]
                    result["overall_accuracy"] = sum(scores) / len(scores)
                
                return result
        except:
            pass
        
        return None