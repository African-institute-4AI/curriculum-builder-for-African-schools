# main.py
import asyncio
import uvicorn
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from src.education_ai_system.api import (
    embeddings_routes,
    docx_conversion_routes,
    content_routes,
    evaluation_routes
)
from src.education_ai_system.utils.session_manager import SessionManager

load_dotenv()

app = FastAPI(
    title="Curriculum Builder API",
    description="API for Nigerian Curriculum Content Generation",
    version="1.0.0"
)

# main.py (after app = FastAPI(...))
# frontend_origin = os.getenv("FRONTEND_ORIGIN")  # e.g., https://your-app.streamlit.app

# origins = ["http://localhost:8501"]
# Update the CORS configuration section
origins = [
    "http://localhost:8501",
    "https://*.hf.space",  # Allow Hugging Face Spaces
    "https://*.streamlit.app",
    
]


# if frontend_origin:
#     origins.append(frontend_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_mgr = SessionManager()

# Include all routers

app.include_router(
    embeddings_routes.router,
    prefix="/api/embeddings",
    tags=["PDF Processing"]
)
app.include_router(
    content_routes.router,
    prefix="/api/content",
    tags=["Content Generation"]
)

app.include_router(
    docx_conversion_routes.router,
    prefix="/api/convert",
    tags=["Document Conversion"]
)

# Add after other app.include_router calls
app.include_router(
    evaluation_routes.router,
    prefix="/api/evaluate",
    tags=["Content Evaluation"]
)

@app.get("/")
async def health_check():
    return {
        "status": "active",
        "version": app.version,
        "endpoints": {
            "process_pdf": "/api/embeddings/process_pdf",
            "clear_database": "/api/embeddings/clear_database",
            "generate_lesson_plan": "/api/content/generate/lesson_plan",
            "generate_scheme": "/api/content/generate/scheme_of_work",
            "generate_notes": "/api/content/generate/lesson_notes",
            'get_exam': "/api/content/generate/exam_generator",
            "convert_docx": "/api/convert/convert_md_to_docx",
            "evaluate_lesson_plan": "/api/evaluate/lesson_plan",
            "evaluate_scheme": "/api/evaluate/scheme",
            "evaluate_lesson_note": "/api/evaluate/lesson_note",
        }
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)