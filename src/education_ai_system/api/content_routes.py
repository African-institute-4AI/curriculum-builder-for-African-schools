#import needed package from fastapi
from pathlib import Path
import traceback
from fastapi import APIRouter, Body, HTTPException
import yaml
#import class ContentGenerator from folder services.generator
from src.education_ai_system.services.generators import ContentGenerator
#import class VectorizationService from services.pinecone_service
from src.education_ai_system.services.pinecone_service import VectorizationService
#import the needed functions from utils.validators
from src.education_ai_system.utils.validators import validate_user_input, extract_week_topic, extract_week_content
#import class SessionManager from utils.session manager
from src.education_ai_system.utils.session_manager import SessionManager
#import class PineconeRetrievalTool from tools.pinecone_exa_tools
from src.education_ai_system.tools.pinecone_exa_tools import PineconeRetrievalTool
#import json to handle data
import json

#create apirouter object that will be used in main.py to access this route
router = APIRouter()
#create ContentGenerator object that is country aware
generator = ContentGenerator(country="nigeria")
#create SessionManager object
session_mgr = SessionManager()

# This is a post request route that will be used by the client side (browser) to pass or post data to the api. 
@router.post("/scheme-of-work")
async def generate_scheme(payload : dict = Body(...)):
    """
    It uses Body parameter which will be used in the Fastapi request body.
    The api is going to extract the data as a JSON (python dictionary) 
    Generate scheme of work - country specified in payload
    """
     # Country is now part of the request body
    country = payload.get('country', 'nigeria')  # Default to nigeria
    
    #validate the input by the user, raise exception if invalid
    if not validate_user_input(payload):
        raise HTTPException(400, detail="Invalid input parameters")
    
    try:

        # Create country-aware retrieval tool
        # create a pinecone object to retrieve context
        retrieval_tool = PineconeRetrievalTool(country=country)
        
        # DEBUG: Check what's in the index
        print(f"🔍 DEBUG: Checking index contents for {country} - payload: {payload}")
        retrieval_tool.debug_index_contents()
        
        #converting the user payload - dictionary (data passed via request body) 
        #to json string then pass it to retrieval_tool run method 
        #before converting back to python dictionary (as result)
        #this will be used to search Pinecone when generating lesson plan
        result = json.loads(retrieval_tool.run(json.dumps(payload)))
        
        if result.get('status') != 'valid':
            raise HTTPException(400, detail="Failed to retrieve context: " + result.get('message', ''))
        
        #use the python dict returned above to get context using the key 'context' or 
        #give it empty string if not found
        context = result.get('context', '')
        print(f"🔍 DEBUG: Context retrieved from Pinecone: {len(context)} characters")
        print(f"🔍 DEBUG: Context preview: {context[:300]}...")
        
        # the session manager is using supabase manager object created in supabase manager class (supabase)
        #then access the store_context method of the supabase manager class to store the context generated 
        #into the database
        context_id = session_mgr.supabase.store_context(
            payload['subject'],
            payload['grade_level'],
            payload['topic'],
            context,
            country = country
        )
        
        # access the content generanator object (generator) then through that use the generate method 
        # by passing it the content type (scheme of work) and context, which was generated above
        scheme_content = generator.generate("scheme_of_work", {
            **payload,
            "curriculum_context": context,
            "country": country  # Add country to the context
        })
        
        # access the create_scheme method in session manager class to create scheme which will be stored 
        # in the supadatabase
        scheme_id = session_mgr.create_scheme({
            "payload": payload,
            "content": scheme_content,
            "context_id": context_id
        })
        
        return {
            "scheme_of_work_id": scheme_id,
            "context_id": context_id,
            "scheme_of_work_output": scheme_content,
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(500, detail=str(e))

# Update generate_lesson_plan endpoint
@router.post("/lesson-plan")
async def generate_lesson_plan(payload: dict = Body(...)):
    """
    create a post request to the api using the Body parameter which tells the api to use data 
    from the request body. To generate lesson plan we have to use the scheme of work id and week number
    """
    scheme_id = payload.get("scheme_of_work_id") #get scheme of work id
    week = str(payload.get("week")) #get week
    
    if not scheme_id or not session_mgr.get_scheme(scheme_id):
        raise HTTPException(400, detail="Invalid scheme ID")
    
    try:
        # use the get_scheme method from the session manager to get the schema from the supabase database 
        scheme_data = session_mgr.get_scheme(scheme_id)
        if not scheme_data:
            raise HTTPException(404, detail="Associated scheme not found")
        
        # Retrieve context from scheme
        context_id = scheme_data.get("context_id")
        if not context_id:
            raise HTTPException(400, detail="No context found for scheme")

        # Extract the full scheme content and then the week-specific topic
        scheme_content = scheme_data.get("content", "")
        #use the extract week topic method from validate package to extract the topic from the scheme table
        week_topic = extract_week_topic(scheme_content, week)
        if not week_topic:
            raise HTTPException(400, detail=f"No topic found for week {week}")

        # Extract other subject details from scheme payload
        scheme_payload = scheme_data.get("payload", {})

        # Generate lesson plan content with week-specific topic and constraints
        lesson_content = generator.generate("lesson_plan", {
            "subject": scheme_payload.get("subject", ""),
            "grade_level": scheme_payload.get("grade_level", ""),
            "topic": week_topic,
            "curriculum_context": scheme_content,
            "teaching_constraints": payload.get("limitations", ""),
            "week": week
        })
        
        # Store in database
        lesson_plan_id = session_mgr.create_lesson_plan(scheme_id, {
            "payload": {
                "subject": scheme_payload.get("subject", ""),
                "grade_level": scheme_payload.get("grade_level", ""),
                "topic": week_topic,
                "limitations": payload.get("limitations", ""),
                "week": week
            },
            "content": lesson_content,
            "context_id": context_id
        })
        
        return {
            "scheme_of_work_id": scheme_id,
            "lesson_plan_id": lesson_plan_id,
            "lesson_plan_output": lesson_content,
            "context_id": context_id,
            "week": week,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))

# Update generate_lesson_notes endpoint
@router.post("/lesson-notes")
async def generate_notes(payload: dict = Body(...)):
    """
    create a post request to the api using the Body parameter which tells the api to use data 
    from the request body. To generate lesson notes we have to use the scheme of work id and lesson plan id and week number
    """
    required_fields = ["scheme_of_work_id", "lesson_plan_id", "week"]
    if any(field not in payload for field in required_fields):
        raise HTTPException(400, detail="Missing required fields in payload")

    scheme_id = payload["scheme_of_work_id"]
    lesson_plan_id = payload["lesson_plan_id"]
    week = str(payload["week"])
    
    try:
        # Get database records
        scheme = session_mgr.get_scheme(scheme_id)
        lesson_plan = session_mgr.get_lesson_plan(lesson_plan_id)
        
        if not scheme or not lesson_plan:
            raise HTTPException(404, detail="Associated content not found")

        # Extract context ID from scheme
        context_id = scheme.get("context_id")
        if not context_id:
            raise HTTPException(400, detail="Scheme is missing context ID")

        # Extract week-specific content
        scheme_week_content = extract_week_content(scheme.get("content", ""), week)
        lesson_plan_week_content = extract_week_content(lesson_plan.get("content", ""), week)

        # Generate notes with week-specific content
        notes_content = generator.generate("lesson_notes", {
            "subject": payload.get("subject", scheme.get("payload", {}).get("subject", "")),
            "grade_level": payload.get("grade_level", scheme.get("payload", {}).get("grade_level", "")),
            "topic": payload.get("topic", scheme.get("payload", {}).get("topic", "")),
            "week": week,
            "scheme_context": scheme_week_content,
            "lesson_plan_context": lesson_plan_week_content
        })
        
        # Store in database with context_id
        notes_id = session_mgr.create_lesson_notes(
            scheme_id,
            lesson_plan_id,
            {
                "payload": {
                    "teaching_method": payload.get("teaching_method", ""),
                    "topic": payload.get("topic", ""),
                    "week": week
                },
                "content": notes_content,
                "context_id": context_id  # Add context ID to lesson notes
            }
        )
        
        return {
            "scheme_of_work_id": scheme_id,
            "lesson_plan_id": lesson_plan_id,
            "lesson_notes_id": notes_id,
            "content": notes_content,
            "context_id": context_id,  # Return context ID in response
            "week": week,
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(500, detail=f"Generation failed: {str(e)}")
    


# @router.post("/exam-generator")
# async def generate_exam(payload: dict = Body(...)):
#     """
#     Generate exam based on existing lesson plan and lesson notes
#     Required fields: scheme_of_work_id, lesson_plan_id, lesson_notes_id, week
#     Optional fields: exam_duration, total_marks, question_types, num_questions
#     """
#     required_fields = ["scheme_of_work_id", "lesson_plan_id", "lesson_notes_id", "week"]
#     if any(field not in payload for field in required_fields):
#         raise HTTPException(400, detail="Missing required fields in payload")

#     scheme_id = payload["scheme_of_work_id"]
#     lesson_plan_id = payload["lesson_plan_id"]
#     lesson_notes_id = payload["lesson_notes_id"]
#     week = payload["week"]
    
#     try:
#         # Get database records
#         scheme = session_mgr.get_scheme(scheme_id)
#         lesson_plan = session_mgr.get_lesson_plan(lesson_plan_id)
#         lesson_notes = session_mgr.get_lesson_notes(lesson_notes_id)
        
#         if not scheme or not lesson_plan or not lesson_notes:
#             raise HTTPException(404, detail="Associated content not found")

#         # Extract context ID from scheme
#         context_id = scheme.get("context_id")
#         if not context_id:
#             raise HTTPException(400, detail="Scheme is missing context ID")

#         # Extract week-specific content from lesson plan and lesson notes
#         lesson_plan_content = extract_week_content(lesson_plan.get("content", ""), week)
#         lesson_notes_content = extract_week_content(lesson_notes.get("content", ""), week)

#         # Get subject details from scheme payload
#         scheme_payload = scheme.get("payload", {})

#         # Generate exam with lesson plan and lesson notes as context
#         exam_content = generator.generate("exam_generator", {
#             "subject": scheme_payload.get("subject", ""),
#             "grade_level": scheme_payload.get("grade_level", ""),
#             "topic": payload.get("topic", scheme_payload.get("topic", "")),
#             "week": week,
#             "exam_duration": payload.get("exam_duration", "2 hours"),
#             "total_marks": payload.get("total_marks", 100),
#             "question_types": payload.get("question_types", "Multiple Choice, Short Answer, Essay"),
#             "num_questions": payload.get("num_questions", 25),
#             "assessment_focus": payload.get("assessment_focus", "Comprehensive assessment covering all learning objectives"),
#             "lesson_plan_context": lesson_plan_content,
#             "lesson_notes_context": lesson_notes_content
#         })
        
#         # Store exam in database with context_id
#         exam_id = session_mgr.create_exam(
#             scheme_id,
#             lesson_plan_id,
#             lesson_notes_id,
#             {
#                 "payload": {
#                     "exam_duration": payload.get("exam_duration", "2 hours"),
#                     "total_marks": payload.get("total_marks", 100),
#                     "question_types": payload.get("question_types", "Multiple Choice, Short Answer, Essay"),
#                     "num_questions": payload.get("num_questions", 25),
#                     "assessment_focus": payload.get("assessment_focus", "Comprehensive assessment covering all learning objectives"),
#                     "week": week
#                 },
#                 "content": exam_content,
#                 "context_id": context_id
#             }
#         )
        
#         return {
#             "scheme_of_work_id": scheme_id,
#             "lesson_plan_id": lesson_plan_id,
#             "lesson_notes_id": lesson_notes_id,
#             "exam_id": exam_id,
#             "content": exam_content,
#             "context_id": context_id,
#             "week": week,
#             "status": "success"
#         }
        
#     except Exception as e:
#         raise HTTPException(500, detail=f"Exam generation failed: {str(e)}")


@router.post("/exam-generator")
async def generate_exam(payload: dict = Body(...)):
    """
    Generate realistic school exams using ALL available teaching materials
    Required: scheme_of_work_id, exam_type
    System automatically finds and uses ALL lesson plans/notes
    """
    required_fields = ["scheme_of_work_id", "exam_type"]
    if any(field not in payload for field in required_fields):
        raise HTTPException(400, detail="Missing required fields")

    scheme_id = payload["scheme_of_work_id"]
    exam_type = payload["exam_type"]
    
    # Get scheme first to determine country
    scheme = session_mgr.get_scheme(scheme_id)
    if not scheme:
        raise HTTPException(404, detail="Scheme not found")
    
    # Extract country from scheme (NO HARDCODING)
    country = scheme.get("payload", {}).get("country", "nigeria")
    
    # Load country-specific exam patterns
    try:
        config_path = Path(__file__).parent.parent / "config" / f"patterns_{country}.yaml"
        with open(config_path, 'r') as file:
            country_patterns = yaml.safe_load(file)
        exam_patterns = country_patterns.get('exam_patterns', {})
    except FileNotFoundError:
        # Fallback to universal patterns
        exam_patterns = {}
    
    # Universal exam configurations with country overrides
    default_configs = {
        "quiz": {
            "weeks_covered": list(range(1, 3)),
            "duration": "30 minutes",
            "total_marks": 20,
            "description": "Weekly Quiz"
        },
        "mid_term": {
            "weeks_covered": list(range(1, 7)),
            "duration": "1.5 hours",
            "total_marks": 50,
            "description": "Mid-Term Examination"
        },
        "end_of_term": {
            "weeks_covered": list(range(1, 13)),
            "duration": "2 hours",
            "total_marks": 100,
            "description": "End of Term Examination"
        },
        "final_exam": {
            "weeks_covered": list(range(1, 37)),
            "duration": "3 hours", 
            "total_marks": 100,
            "description": "Final Examination"
        }
    }
    
    # Merge country-specific patterns with defaults
    exam_configs = {**default_configs, **exam_patterns}
    
    if exam_type not in exam_configs:
        available_types = list(exam_configs.keys())
        raise HTTPException(400, detail=f"Invalid exam type. Available: {available_types}")
    
    config = exam_configs[exam_type]
    
    try:
        # AUTO-EXTRACT all lesson plans and notes for this scheme
        print(f"🔍 Searching for ALL lesson materials for scheme: {scheme_id}")
        
        # Get ALL lesson plans associated with this scheme
        all_lesson_plans = session_mgr.supabase.get_lesson_plans_by_scheme(scheme_id)
        print(f"📚 Found {len(all_lesson_plans)} lesson plans")
        
        # Get ALL lesson notes associated with this scheme  
        all_lesson_notes = session_mgr.supabase.get_lesson_notes_by_scheme(scheme_id)
        print(f"📝 Found {len(all_lesson_notes)} lesson notes")
        
        # Build comprehensive teaching context
        teaching_materials = {
            "scheme_content": scheme.get("content", ""),
            "lesson_plans_content": [],
            "lesson_notes_content": [],
            "covered_topics": []
        }
        
        # Extract content for exam weeks
        for week in config["weeks_covered"]:
            # Get scheme topic for this week
            week_topic = extract_week_topic(teaching_materials["scheme_content"], str(week))
            if week_topic:
                teaching_materials["covered_topics"].append(f"Week {week}: {week_topic}")
            
            # Find lesson plan for this week
            # week_lesson_plan = next(
            #     (plan for plan in all_lesson_plans 
            #      if plan.get("payload", {}).get("week") == str(week)), 
            #     None
            # )
            week_lesson_plan = next(
                (plan for plan in all_lesson_plans 
                if str(plan.get("payload", {}).get("week", "")) == str(week)), 
                None
)
            if week_lesson_plan:
                content = extract_week_content(week_lesson_plan.get("content", ""), str(week))
                teaching_materials["lesson_plans_content"].append(f"Week {week} Plan:\n{content}")
            
            # Find lesson notes for this week
            # week_lesson_notes = next(
            #     (notes for notes in all_lesson_notes 
            #      if notes.get("payload", {}).get("week") == str(week)), 
            #     None
            # )
            week_lesson_notes = next(
                (notes for notes in all_lesson_notes 
                if str(notes.get("payload", {}).get("week", "")) == str(week)), 
                None
)
            if week_lesson_notes:
                content = extract_week_content(week_lesson_notes.get("content", ""), str(week))
                teaching_materials["lesson_notes_content"].append(f"Week {week} Notes:\n{content}")

        # Get scheme details
        scheme_payload = scheme.get("payload", {})
        context_id = scheme.get("context_id")
        
        print(f"📊 Exam context: {len(teaching_materials['lesson_plans_content'])} lesson plans, {len(teaching_materials['lesson_notes_content'])} lesson notes")
        
        # # Generate comprehensive exam using ALL materials
        # exam_content = generator.generate("exam_generator", {
        #     "subject": scheme_payload.get("subject", ""),
        #     "grade_level": scheme_payload.get("grade_level", ""),
        #     "topic": scheme_payload.get("topic", ""),
        #     "country": country,
        #     "exam_type": exam_type,
        #     "weeks_covered": config["weeks_covered"],
        #     "exam_duration": payload.get("exam_duration", config["duration"]),
        #     "total_marks": payload.get("total_marks", config["total_marks"]),
        #     "question_types": payload.get("question_types", "Multiple Choice, Short Answer, Essay"),
        #     "num_questions": payload.get("num_questions", 25),
        #     "assessment_focus": payload.get("assessment_focus", "Comprehensive assessment covering all learning objectives"),
            
        #     # COMPREHENSIVE CONTEXT from ALL teaching materials
        #     "scheme_context": teaching_materials["scheme_content"],
        #     "lesson_plans_context": "\n\n".join(teaching_materials["lesson_plans_content"]) if teaching_materials["lesson_plans_content"] else "No lesson plans available for covered weeks",
        #     "lesson_notes_context": "\n\n".join(teaching_materials["lesson_notes_content"]) if teaching_materials["lesson_notes_content"] else "No lesson notes available for covered weeks",
        #     "covered_topics": "\n".join(teaching_materials["covered_topics"])
        # })

        # Initialize exam_content
        exam_content = ""
        # Generate comprehensive exam using ALL materials
        try:
            exam_content = generator.generate("exam_generator", {
                "subject": scheme_payload.get("subject", ""),
                "grade_level": scheme_payload.get("grade_level", ""),
                "topic": scheme_payload.get("topic", ""),
                "country": country,
                "exam_type": exam_type,
                "week": str(config["weeks_covered"][0]),
                "weeks_covered": config["weeks_covered"],
                "exam_duration": payload.get("exam_duration", config["duration"]),
                "total_marks": payload.get("total_marks", config["total_marks"]),
                "question_types": payload.get("question_types", "Multiple Choice, Short Answer, Essay"),
                "num_questions": payload.get("num_questions", 25),
                "assessment_focus": payload.get("assessment_focus", "Comprehensive assessment covering all learning objectives"),
                
                # COMPREHENSIVE CONTEXT from ALL teaching materials
                "scheme_context": teaching_materials["scheme_content"],
                "lesson_plans_context": "\n\n".join(teaching_materials["lesson_plans_content"]) if teaching_materials["lesson_plans_content"] else "No lesson plans available for covered weeks",
                "lesson_notes_context": "\n\n".join(teaching_materials["lesson_notes_content"]) if teaching_materials["lesson_notes_content"] else "No lesson notes available for covered weeks",
                "covered_topics": "\n".join(teaching_materials["covered_topics"])
            })
        except Exception as e:
            print(f"❌ EXAM GENERATION ERROR: {str(e)}")
            print(f"❌ ERROR TYPE: {type(e)}")
            traceback.print_exc()
        
        # Store exam in database
        exam_id = session_mgr.create_exam(
            scheme_id,
            None,  # No single lesson plan - uses multiple
            None,  # No single lesson notes - uses multiple
            {
                "payload": {
                    "exam_type": exam_type,
                    "weeks_covered": config["weeks_covered"],
                    "exam_duration": config["duration"],
                    "total_marks": config["total_marks"],
                    "country": country,
                    "materials_used": {
                        "lesson_plans": len(teaching_materials["lesson_plans_content"]),
                        "lesson_notes": len(teaching_materials["lesson_notes_content"])
                    }
                },
                "content": exam_content,
                "context_id": context_id
            }
        )
        
        return {
            "exam_id": exam_id,
            "exam_type": exam_type,
            "weeks_covered": config["weeks_covered"],
            "country": country,
            "materials_used": {
                "scheme": True,
                "lesson_plans": len(teaching_materials["lesson_plans_content"]),
                "lesson_notes": len(teaching_materials["lesson_notes_content"])
            },
            "content": exam_content,
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(500, detail=f"Exam generation failed: {str(e)}")