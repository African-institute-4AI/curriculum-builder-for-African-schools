#import needed package from fastapi
from fastapi import APIRouter, HTTPException, Body
#file upload package
from fastapi.responses import FileResponse
#for background tasks
from fastapi.background import BackgroundTasks
#from file_operations package import convert md to docx
from src.education_ai_system.utils.file_operations import convert_md_to_docx
from pathlib import Path
import os
from datetime import datetime
#import supabasemanager class
from src.education_ai_system.utils.supabase_manager import SupabaseManager

router = APIRouter()

def cleanup_files(md_path: Path, docx_path: Path):
    """Cleanup temporary files after response is sent"""
    try:
        if md_path.exists():
            os.remove(md_path)
        if docx_path.exists():
            os.remove(docx_path)
    except Exception as e:
        print(f"Error cleaning files: {str(e)}")

@router.post("/generate-document")
async def generate_document(
    background_tasks: BackgroundTasks,
    content_type: str = Body(...),
    scheme_of_work_id: str = Body(None),
    lesson_plan_id: str = Body(None),
    lesson_notes_id: str = Body(None),
    exam_id : str = Body(None),
    custom_filename: str = Body(None)
):
    md_path = None
    docx_path = None

    try:
        content = None
        supabase = SupabaseManager()

        if content_type == "scheme":
            scheme = supabase.get_scheme(scheme_of_work_id)
            if not scheme:
                raise HTTPException(404, detail="Scheme not found")
            content = scheme.get("content")
            metadata = scheme.get("payload")

        elif content_type == "lesson_plan":
            lesson_plan = supabase.get_lesson_plan(lesson_plan_id)
            if not lesson_plan:
                raise HTTPException(404, detail="Lesson plan not found")
            content = lesson_plan.get("content")
            metadata = lesson_plan.get("payload")

        elif content_type == "lesson_notes":
            notes = supabase.get_lesson_notes(lesson_notes_id)
            if not notes:
                raise HTTPException(404, detail="Lesson notes not found")
            content = notes.get("content")
            metadata = notes.get("payload")

        elif content_type == 'exam_generator':
            exam = supabase.get_exam(exam_id)
            if not exam:
                raise HTTPException(404, details='exam note found')
            content = exam.get('content')
            metadata = exam.get('payload')

        # Validate content exists
        if not content:
            raise HTTPException(404, detail="Content not found in stored data")

        # Create temporary directory
        temp_dir = Path("temp_docs")
        temp_dir.mkdir(exist_ok=True, parents=True)
        
        # Create filenames
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        base_name = f"{custom_filename or content_type}_{timestamp}"
        md_path = temp_dir / f"{base_name}.md"
        docx_path = temp_dir / f"{base_name}.docx"

        # Write content to markdown file
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Convert to DOCX
        convert_md_to_docx(md_path, docx_path)

        if not docx_path.exists():
            raise HTTPException(500, detail="DOCX conversion failed - no output file created")

        # Add cleanup task
        background_tasks.add_task(cleanup_files, md_path, docx_path)

        return FileResponse(
            docx_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{base_name}.docx",
            headers={"Content-Disposition": f"attachment; filename={base_name}.docx"}
        )

    except HTTPException:
        raise
    except Exception as e:
        # Cleanup immediately if error occurs
        if md_path and md_path.exists():
            os.remove(md_path)
        if docx_path and docx_path.exists():
            os.remove(docx_path)
        raise HTTPException(500, detail=f"Conversion failed: {str(e)}")

