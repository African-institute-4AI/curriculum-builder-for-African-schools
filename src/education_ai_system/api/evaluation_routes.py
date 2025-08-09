from fastapi import APIRouter, Body, HTTPException
from src.education_ai_system.services.evaluation_service import ContentEvaluator
from src.education_ai_system.utils.session_manager import SessionManager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SupabaseManager")
session_mgr = SessionManager()
router = APIRouter()
evaluator = ContentEvaluator()

# Update evaluate_scheme to use context_id
@router.post("/scheme")
async def evaluate_scheme(context_id: str = Body(..., embed=True)):
    try:
        # First ensure context exists
        context_data = session_mgr.supabase.get_context_by_id(context_id)
        if not context_data:
            raise HTTPException(404, detail="Context not found")
        
        scheme = session_mgr.supabase.get_scheme_by_context(context_id)
        if not scheme:
            raise HTTPException(404, detail="Associated scheme not found")
        
        print(f"\n[EVALUATION REQUEST] Scheme with context ID: {context_id}")
        result = evaluator.evaluate_content_by_context("scheme_of_work", context_id)
        
        # Add debug information to error responses
        if result.get('status') == 'error':
            result['context_id'] = context_id
            result['content_type'] = "scheme_of_work"
            
        print(f"[EVALUATION RESULT] Status: {result.get('status')}")
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Evaluation failed: {str(e)}",
            "context_id": context_id
        }

# Update evaluate_lesson_plan to use context_id
@router.post("/lesson_plan")
async def evaluate_lesson_plan(lesson_plan_id: str = Body(..., embed=True)):  # Change to lesson_plan_id
    try:
        # Get lesson plan using ID
        lesson_plan = session_mgr.supabase.get_lesson_plan(lesson_plan_id)
        if not lesson_plan:
            raise HTTPException(404, detail="Lesson plan not found")
        
        # Get context ID from lesson plan
        context_id = lesson_plan.get("context_id")
        if not context_id:
            raise HTTPException(400, detail="No context associated with lesson plan")
            
        result = evaluator.evaluate_content_by_context("lesson_plan", context_id)
        return result
    except Exception as e:
        return {
            "status": "error",
            "message": f"Evaluation failed: {str(e)}",
            "lesson_plan_id": lesson_plan_id
        }

# Update evaluate_lesson_notes to use context_id
@router.post("/lesson_notes")
async def evaluate_lesson_notes(lesson_notes_id: str = Body(..., embed=True)):
    try:
        logger.info(f"Starting evaluation for lesson_notes_id: {lesson_notes_id}")
        
        lesson_notes = session_mgr.supabase.get_lesson_notes(lesson_notes_id)
        if not lesson_notes:
            logger.error(f"Lesson notes not found: {lesson_notes_id}")
            raise HTTPException(404, detail="Lesson notes not found")
        
        scheme_id = lesson_notes.get("scheme_id")
        logger.info(f"Found associated scheme_id: {scheme_id}")
        
        scheme = session_mgr.supabase.get_scheme(scheme_id)
        if not scheme:
            logger.error(f"Scheme not found: {scheme_id}")
            raise HTTPException(404, detail="Associated scheme not found")
        
        context_id = scheme.get("context_id")
        logger.info(f"Found context_id: {context_id}")
        
        if not context_id:
            logger.error("No context_id found in scheme")
            raise HTTPException(400, detail="No context found for scheme")
        
        logger.info(f"Starting evaluation for context_id: {context_id}")
        result = evaluator.evaluate_content_by_context("lesson_notes", context_id)
        
        logger.info(f"Evaluation completed: {result.get('status')}")
        return result
        
    except Exception as e:
        logger.exception("Evaluation failed")
        return {
            "status": "error",
            "message": f"Evaluation failed: {str(e)}",
            "lesson_notes_id": lesson_notes_id
        }
