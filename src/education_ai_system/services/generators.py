# from langchain_openai import ChatOpenAI
from pathlib import Path
from langchain_groq import ChatGroq
from src.education_ai_system.utils.validators import load_prompt
import yaml

class ContentGenerator:
    def __init__(self, country: str = "nigeria"):
        self.country = country
        self.country_context = self._load_country_context()
        #to generate after embedding the document in Pinecone vector database
        #a model is used with the following specifications
        self.llm = ChatGroq(
                    temperature=0.3, #randomness of output generated
                    model_name="llama3-70b-8192", #model used
                    max_tokens=4096 #max token to be generated
                    )
        #use the load prompt method from validators package to load the predefined prompts
        # which will be used be the model to generate outputs later              
        self.prompts = {
            "lesson_plan": load_prompt("lesson_plan"),
            "scheme_of_work": load_prompt("scheme_of_work"),
            "lesson_notes": load_prompt("lesson_notes"),
            "exam_generator": load_prompt("exam_generator")
        }
    
    def _load_country_context(self):
            """Load country-specific context for generation"""
            config_path = Path(__file__).parent.parent / "config" / f"patterns_{self.country}.yaml"
            try:
                with open(config_path, 'r') as file:
                    return yaml.safe_load(file)
            except FileNotFoundError:
                # Fallback to Nigeria
                config_path = Path(__file__).parent.parent / "config" / "patterns_nigeria.yaml"
                with open(config_path, 'r') as file:
                    return yaml.safe_load(file)

    def generate(self, content_type: str, context: dict):
        #build your prompt using the buile prompt method with the prompt template
        prompt = self._build_prompt(content_type, context)
        try:
            #you only need the content that will be returned by the model, so you get only that
            return self.llm.invoke(prompt).content
        except Exception as e:
            return f"Error generating content: {str(e)}"

    #uses the content type which can be (scheme of work, lesson plan etc) as the key word for the 
    #class instance (prompt) to load a predefined template from the config folder
    def _build_prompt(self, content_type: str, context: dict):
        template = self.prompts[content_type]
        
        """
        uses the lesson note prompt file to pass in the context dict value in their respective placeholder
        And the same thing will be done for lesson plan and exam generator 
        """
        
        # Get country from context or use default
        country = context.get('country', self.country)

        if content_type == "scheme_of_work":
            return template.format(
                subject=context['subject'],
                grade_level=context['grade_level'],
                topic=context['topic'],
                curriculum_context=context.get('curriculum_context', ''),
                country=country.title()  # Capitalize country name
            )

        if content_type == "lesson_notes":
            return template.format(
                subject=context['subject'],
                grade_level=context['grade_level'],
                topic=context['topic'],
                week=context['week'],
                scheme_context=context.get('scheme_context', ''),
                country=country.title(), 
                lesson_plan_context=context.get('lesson_plan_context', '')
            )
        elif content_type == "lesson_plan":
            return template.format(
                subject=context['subject'],
                grade_level=context['grade_level'],
                topic=context['topic'],
                week=context.get('week', '1'),  # Add week
                curriculum_context=context.get('curriculum_context', ''),
                teaching_constraints=context.get('teaching_constraints', 'No constraints provided'),
                country=country.title()  # Capitalize country name
            )
        
        elif content_type == "exam_generator":
            return template.format(
                subject=context['subject'],
                grade_level=context['grade_level'],
                topic=context['topic'],
                country=context.get('country', self.country).title(),
                exam_type=context.get('exam_type', 'quiz'),
                weeks_covered=context.get('weeks_covered', [1]),
                scheme_context=context.get('scheme_context', ''),
                covered_topics=context.get('covered_topics', ''),
                exam_duration=context.get('exam_duration', '2 hours'),
                total_marks=context.get('total_marks', 100),
                question_types=context.get('question_types', 'Multiple Choice, Short Answer, Essay'),
                num_questions=context.get('num_questions', 25),
                assessment_focus=context.get('assessment_focus', 'Comprehensive assessment covering all learning objectives'),
                lesson_plan_context=context.get('lesson_plan_context', ''),
                lesson_notes_context=context.get('lesson_notes_context', '')
            )
        # Other content types remain the same
        return template.format(
            subject=context['subject'],
            grade_level=context['grade_level'],
            topic=context['topic'],
            curriculum_context=context.get('curriculum', '')
        )