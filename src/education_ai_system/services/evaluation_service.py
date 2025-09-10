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
import yaml
from pathlib import Path

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
    """
    This class is used to evaluate the content of a scheme of work, lesson plan, or lesson notes.
    It uses the LLM to evaluate the content and return a score and reason for the evaluation.
    """
    def __init__(self):
        #create the llm as a judge model to be used for evaluation
        self.llm = ChatGroq(
            temperature=0,
            model_name="gemma2-9b-it",  # Using the best available Groq model
            max_tokens=1024
        )
        #create the retriever to be used for retrieval of context
        self.retriever = PineconeRetrievalTool()
        #this will help enforce how the response from the judge is structured and validated
        self.parser = PydanticOutputParser(pydantic_object=EvaluationResult)
        #create the prompt template to be used for the evaluation
        self.prompt_template = self._create_prompt_template()
        
        # Load evaluation weights
        self.evaluation_weights = self._load_evaluation_weights()

        # Load improvement prompt
        self.editor_template = load_prompt("improve_editor")


    def _load_evaluation_weights(self):
        """Load country-specific evaluation weights"""
        config_path = Path(__file__).parent.parent / "config" / "evaluation_weight.yaml"
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            print(f"⚠️ Evaluation weights file not found, using default weights")
            return {}
    
    def _create_prompt_template(self):
        #load the base prompt from the prompts folder
        base_template = load_prompt("evaluation")
        
        # Create new template with format instructions that will be as prompt for the llm
        #this will be done authomatically by the PydanticOutputParser class using the parser variable
        return PromptTemplate(
            template=base_template + "\n{format_instructions}",
            input_variables=[
                "content_type", 
                "subject", 
                "grade_level", 
                "topic",
                "reference_materials",
                "content",
                "country"
            ],
            partial_variables={
                "format_instructions": self.parser.get_format_instructions()
            }
        )

    # evaluation_service.py
    def evaluate_content_by_context(self, content_type: str, context_id: str) -> dict:
        """This method will be used to evaluate the content of a scheme of work, lesson plan, lesson notes or exam questions"""
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
            elif content_type == "exam_generator":
                content_data = supabase.get_exam_by_context(context_id)
            else:
                print("❌ ERROR: Invalid content type specified")
                return {"status": "error", "message": "Invalid content type"}
            
            if not content_data:
                print("❌ ERROR: Content not found for given context")
                return {"status": "error", "message": "Content not found for given context"}
            print("✅ Content retrieved successfully")
            print(f"Content ID: {content_data.get('id')}")
            
        
            #this line will prepare the evaluation input data for the llm
            print("Building evaluation input...")
            input_data = {
                "content_type": content_type,
                "subject": context_data["subject"],
                "grade_level": context_data["grade_level"],
                "topic": context_data["topic"],
                # "curriculum": context_data["context"],
                "reference_materials": self._build_reference_context(content_type, context_data, context_data, supabase),
                "content": content_data["content"],
                "country": content_data.get("country", 'nigeria')
            }
            
            #this line will format the prompt with the structured instructions automatically using the input data
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
                #this line will parse the response from the llm using the parser variable
                #this will help enforce how the response is structured and validated
                evaluation_data = self.parser.parse(response.content)
                print("✅ Successfully parsed evaluation response")
                
                # Convert to dict for serialization
                result = evaluation_data.dict()
                result["status"] = "success"

                # Calculate weighted overall accuracy
                result["overall_accuracy"] = self._calculate_weighted_accuracy(
                    result["accuracy"], 
                    context_data.get("country", "nigeria"), 
                    content_type
                )
                # Add composite score
                result["composite_score"] = self._calculate_composite_score(
                    result["overall_accuracy"],
                    result.get("bias", {})
                )
            
                #decide if improvement is needed (single pass)
                needs_improvement = False
                low_metrics = []
                threshold = 4
                # bias_threshold = 5 

                for metric_name, metric_data in result.get("accuracy", {}).items():
                    if metric_data.get('score', 0) < threshold:
                        low_metrics.append(metric_name)
                        needs_improvement = True

                bias_score = result.get('bias', {}).get("score", 0)
                if bias_score < threshold:
                    low_metrics.append("bias")
                    needs_improvement = True
                
                overall_min = 4.0
                if result.get("overall_accuracy", 0) < overall_min:
                    needs_improvement = True

                
                improved = {
                    "improved_content": None,
                    "change_log": []
                }
                if needs_improvement:
                    improved = self._regenerate_with_feedback(
                        content_type = content_type,
                        context_data=context_data,
                        content_data=content_data,
                        evaluation=result

                    )
                    if improved.get("improved_content"):
                        reeval_input = dict(input_data)
                        reeval_input['content'] = improved['improved_content']
                        reeval_prompt = self.prompt_template.format_prompt(**reeval_input).to_string()

                        try:
                            reeval_resp = self.llm.invoke(reeval_prompt)
                            reeval_data = self.parser.parse(reeval_resp.content).dict()
                            reeval_data['overall_accuracy'] = self._calculate_weighted_accuracy(
                                reeval_data['accuracy'],
                                context_data.get("country", 'nigeria'),
                                content_type

                            )
                            result['improved_evaluation'] = reeval_data
                        except Exception as e:
                            print(f"Re-evaluation failed: {e}")

                result['improved_content'] = improved.get("improved_content")
                result['change_log'] = improved.get("change_log")
                result['needs_improvement'] = needs_improvement
                result['low_metrics'] = low_metrics
                

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

    def _calculate_weighted_accuracy(self, accuracy_scores: dict, country: str, content_type: str) -> float:
        """Calculate weighted overall accuracy using country-specific weights"""
        try:
            weights = self.evaluation_weights.get(country, {}).get(content_type, {})
            if not weights:
                # Fallback to equal weights
                scores = [score["score"] for score in accuracy_scores.values()]
                return round(sum(scores) / len(scores), 1)
            
            weighted_sum = 0
            for criterion, score_data in accuracy_scores.items():
                weight = weights.get(criterion, 0.2)  # Default weight
                weighted_sum += score_data["score"] * weight
            
            return round(weighted_sum, 1)
        except Exception as e:
            print(f"Error calculating weighted accuracy: {e}")
            # Fallback to simple average
            scores = [score["score"] for score in accuracy_scores.values()]
            return round(sum(scores) / len(scores), 1)
        
    def _calculate_composite_score(self, overall_accuracy: float, bias_score: dict) -> float:
        """Calculate composite score combining accuracy and bias"""
        try:
            bias_value = bias_score.get("score", 0) if bias_score else 0
            
            # Option 1: Weighted average (80% accuracy, 20% bias)
            composite = (overall_accuracy * 0.8) + (bias_value * 0.2)
            
            # Option 2: Simple average
            # composite = (overall_accuracy + bias_value) / 2
            
            # Option 3: Penalty system (if bias < 4, reduce accuracy)
            # if bias_value < 4:
            #     composite = overall_accuracy * 0.9
            # else:
            #     composite = overall_accuracy
            
            return round(composite, 1)
        except Exception as e:
            print(f"Error calculating composite score: {e}")
            return overall_accuracy
                
    def _build_reference_context(self, content_type: str, context_data: dict, content_data: dict, supabase) -> str:
        # Scheme of work → compare to curriculum context
        if content_type == "scheme_of_work":
            return context_data.get("context", "")

        # Lesson plan → compare to its scheme content (fallback to curriculum)
        if content_type == "lesson_plan":
            scheme_id = content_data.get("scheme_id")
            scheme = supabase.get_scheme(scheme_id) if scheme_id else None
            return (scheme or {}).get("content", context_data.get("context", ""))

        # Lesson notes → compare to lesson plan + scheme (fallbacks applied)
        if content_type == "lesson_notes":
            scheme_id = content_data.get("scheme_id")
            lesson_plan_id = content_data.get("lesson_plan_id")
            scheme = supabase.get_scheme(scheme_id) if scheme_id else None
            lesson_plan = supabase.get_lesson_plan(lesson_plan_id) if lesson_plan_id else None

            parts = []
            if scheme and scheme.get("content"):
                parts.append(f"SCHEME:\n{scheme['content']}")
            if lesson_plan and lesson_plan.get("content"):
                parts.append(f"LESSON PLAN:\n{lesson_plan['content']}")
            return "\n\n".join(parts) if parts else context_data.get("context", "")

        # Exam → compare to scheme + ALL lesson plans + ALL lesson notes for the scheme
        if content_type == "exam_generator":
            scheme_id = content_data.get("scheme_id")
            parts = []

            scheme = supabase.get_scheme(scheme_id) if scheme_id else None
            if scheme and scheme.get("content"):
                parts.append(f"SCHEME:\n{scheme['content']}")

            plans = supabase.get_lesson_plans_by_scheme(scheme_id) if scheme_id else []
            if plans:
                plans_text = "\n\n".join(
                    f"Lesson Plan (week {p.get('payload', {}).get('week', '?')}):\n{p.get('content', '')}"
                    for p in plans
                    if p.get("content")
                )
                if plans_text:
                    parts.append(f"ALL LESSON PLANS:\n{plans_text}")

            notes = supabase.get_lesson_notes_by_scheme(scheme_id) if scheme_id else []
            if notes:
                notes_text = "\n\n".join(
                    f"Lesson Notes (week {n.get('payload', {}).get('week', '?')}):\n{n.get('content', '')}"
                    for n in notes
                    if n.get("content")
                )
                if notes_text:
                    parts.append(f"ALL LESSON NOTES:\n{notes_text}")

            return "\n\n".join(parts) if parts else context_data.get("context", "")

        # Fallback
        return context_data.get("context", "")

    

    def _regenerate_with_feedback(self, content_type: str, context_data: dict, content_data: dict, evaluation: dict) -> dict:
        """ 
        This method will help to generate an improved content with the feedback from the judge evaluation
        if the evaluation is not satisfactory.
        """

        editor_llm = ChatGroq(
            temperature=0.1,
            model_name='gemma2-9b-it', 
            max_tokens=4096
        )

        improvement_prompt = self.editor_template.format(
            content_type=content_type,
            country=context_data.get('country', 'nigeria').title(),
            subject=context_data.get('subject', ''),
            grade_level=context_data.get('grade_level', ''),
            topic=context_data.get('topic', ''),
            reference_materials=self._build_reference_context(content_type, context_data, content_data, SupabaseManager()),
            evaluation_json=json.dumps(evaluation, ensure_ascii=False, indent=2), 
            original_content=content_data.get('content', ''),
            threshold=4
        )

        try:
            resp = editor_llm.invoke(improvement_prompt)
            text = resp.content or ""
        except Exception as e:
            return {
                "improved_content": None, 
                "change_log": f"Improvement failed: {str(e)}"
            }

        # Clean and parse the response
        text_raw = text.strip()
        text_clean = (
            text_raw
                .replace("```json", "")
                .replace("```", "")
                .replace("'", "'").replace("'", "'")
                .replace(""", '"').replace(""", '"')
        ).strip()

        def try_json(s: str):
            try:
                return json.loads(s)
            except:
                return None

        # Try direct parse first
        parsed = try_json(text_clean)

        # If not parsed, try extracting the largest JSON object
        if not isinstance(parsed, dict):
            start = text_clean.find('{')
            end = text_clean.rfind('}') + 1
            if start != -1 and end > start:
                parsed = try_json(text_clean[start:end])

        # If still not dict, return raw text as improved content
        if not isinstance(parsed, dict):
            return {
                "improved_content": text_raw,
                "change_log": ["Raw editor response used due to parsing failure"]
            }

        # Handle common shapes
        improved = None
        change_log = parsed.get("change_log", [])

        if "improved_content" in parsed:
            value = parsed.get("improved_content")
            if isinstance(value, str):
                value_str = value.strip()
                # If double-encoded JSON, parse again
                if value_str.startswith("{") and value_str.endswith("}"):
                    inner = try_json(value_str)
                    if isinstance(inner, dict) and "improved_content" in inner:
                        improved = str(inner.get("improved_content", "")).strip()
                        change_log = inner.get("change_log", change_log)
                    else:
                        improved = value_str
                else:
                    improved = value_str
        elif "improved_content_lines" in parsed and isinstance(parsed["improved_content_lines"], list):
            improved = "\n".join(str(x) for x in parsed["improved_content_lines"]).strip()

        return {
            "improved_content": improved,
            "change_log": change_log
        }