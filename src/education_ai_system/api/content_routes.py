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
    from the request body. To generate lesson notes we have to use the scheme of work id and lesson plan id 
    and the same week number as the lesson plan
    """
    required_fields = ["scheme_of_work_id", "lesson_plan_id"]
    # week = str(payload.get("week")) #get week
    if any(field not in payload for field in required_fields):
        raise HTTPException(400, detail="Missing required fields in payload")

    scheme_id = payload["scheme_of_work_id"]
    lesson_plan_id = payload["lesson_plan_id"]
    
    
    try:
        # Get database records
        scheme = session_mgr.get_scheme(scheme_id)
        lesson_plan = session_mgr.get_lesson_plan(lesson_plan_id)
        
        if not scheme or not lesson_plan:
            raise HTTPException(404, detail="Associated content not found")

        #derive week from the lesson plan (authorization)
        lesson_plan_week = str(lesson_plan.get("payload", {}).get('week', '1')).strip()
        if not lesson_plan_week:
            raise HTTPException(400, detail="lesson plan is missing week number")

        week = lesson_plan_week
        
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
    

@router.post("/exam-generator")
async def generate_exam(payload: dict = Body(...)):
    """
    Generate exams based on teacher-selected weeks.
    Required: scheme_of_work_id, weeks (list of week numbers)
    Uses ONLY lesson plans/notes for selected weeks.
    """
    required_fields = ["scheme_of_work_id", "weeks"]
    if any(field not in payload for field in required_fields):
        raise HTTPException(400, detail="Missing required fields: 'scheme_of_work_id', 'weeks'")

    scheme_id = payload["scheme_of_work_id"]
    weeks = payload["weeks"]
    
    if not isinstance(weeks, (list, tuple)) or not weeks:
        raise HTTPException(400, detail="'weeks' must be a non-empty list or tuple")

    try:
        # de-dupe + sort, ensure ints
        weeks = sorted({int(w) for w in weeks})
    except Exception:
        raise HTTPException(400, detail="'weeks' must contain integers")

    # Get scheme first to determine country
    scheme = session_mgr.get_scheme(scheme_id)
    if not scheme:
        raise HTTPException(404, detail="Scheme not found")
    
    # Extract country from scheme (NO HARDCODING)
    country = scheme.get("payload", {}).get("country", "nigeria")
    
    # Optional configs (fallback defaults)
    exam_duration = payload.get("exam_duration", "1 hour")
    total_marks = int(payload.get("total_marks", 50))
    question_types = payload.get("question_types", "Multiple Choice, Short Answer, Essay")
    num_questions = int(payload.get("num_questions", 25))
    assessment_focus = payload.get("assessment_focus", "Assess learning objectives covered in selected weeks")

    try:
        # Gather all lesson plans and notes for the scheme
        all_lesson_plans = session_mgr.supabase.get_lesson_plans_by_scheme(scheme_id)
        all_lesson_notes = session_mgr.supabase.get_lesson_notes_by_scheme(scheme_id)

        # DEBUG visibility to ensure we can see what's stored
        print(f"📚 Found {len(all_lesson_plans)} lesson plans, 📝 {len(all_lesson_notes)} lesson notes for scheme {scheme_id}")
        print("Lesson plan weeks:", [str(p.get('payload', {}).get('week', p.get('week', ''))) for p in all_lesson_plans])
        print("Lesson note weeks:", [str(n.get('payload', {}).get('week', n.get('week', ''))) for n in all_lesson_notes])

        # Build context for the selected weeks only
        teaching_materials = {
            "scheme_content": scheme.get("content", ""),
            "lesson_plans_content": [],
            "lesson_notes_content": [],
            "covered_topics": []
        }

        # Extract content for the selected weeks
        for week in weeks:
            week_str = str(week)

            # scheme topic for this week
            week_topic = extract_week_topic(teaching_materials['scheme_content'], week_str)
            if week_topic:
                teaching_materials['covered_topics'].append(f"Week {week}: {week_topic}")

            # lesson plan for this week (match payload.week OR top-level week; handle int/str)
            week_lesson_plan = next(
                (plan for plan in all_lesson_plans
                 if str(plan.get("payload", {}).get("week", plan.get("week", ""))) == week_str),
                None
            )
            if week_lesson_plan:
                lesson_plan_content = extract_week_content(week_lesson_plan.get("content", ""), week_str)
                teaching_materials["lesson_plans_content"].append(f"Week {week} Plan:\n{lesson_plan_content}")

            # lesson notes for this week (same robust matching)
            week_lesson_notes = next(
                (notes for notes in all_lesson_notes
                 if str(notes.get("payload", {}).get("week", notes.get("week", ""))) == week_str),
                None
            )
            if week_lesson_notes:
                lesson_note_content = extract_week_content(week_lesson_notes.get("content", ""), week_str)
                teaching_materials['lesson_notes_content'].append(f"Week {week} Notes:\n{lesson_note_content}")

        scheme_payload = scheme.get("payload", {})
        context_id = scheme.get("context_id")

        # Generate Exam
        exam_content = generator.generate("exam_generator", {
            "subject": scheme_payload.get("subject", ""),
            "grade_level": scheme_payload.get("grade_level", ""), 
            "topic": scheme_payload.get("topic", ""),
            "country": country,

            "weeks_covered": weeks,
            "exam_duration": exam_duration,
            "total_marks": total_marks,
            "question_types": question_types,
            "num_questions": num_questions,
            "assessment_focus": assessment_focus,

            "scheme_context": teaching_materials['scheme_content'],
            "lesson_plans_context": "\n\n".join(teaching_materials['lesson_plans_content']) 
                if teaching_materials['lesson_plans_content'] else "No lesson plans available for selected weeks",
            "lesson_notes_context": "\n\n".join(teaching_materials['lesson_notes_content']) 
                if teaching_materials['lesson_notes_content'] else "No lesson notes available for selected weeks",
            "covered_topics": "\n".join(teaching_materials['covered_topics'])
        })

        # Store in database
        exam_id = session_mgr.create_exam(
            scheme_id,
            None, 
            None,
            {
                "payload":{
                    "weeks_covered": weeks,
                    "exam_duration": exam_duration,
                    "total_marks": total_marks, 
                    "country": country,
                    "materials_used": {
                        "lesson_plans": len(teaching_materials['lesson_plans_content']),
                        "lesson_notes": len(teaching_materials['lesson_notes_content'])
                    }
                },
                "content": exam_content,
                "context_id": context_id
            }
        )

        return {
            "exam_id": exam_id,
            "weeks_covered": weeks,
            "country": country,
            "materials_used": {
                "scheme": True,
                "lesson_plans": len(teaching_materials["lesson_plans_content"]),
                "lesson_notes": len(teaching_materials["lesson_notes_content"])
            },
            "content": exam_content,
            "status": "success"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=f"Exam generation failed: {str(e)}")

