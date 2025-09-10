from fastapi import APIRouter, Form, UploadFile, File, HTTPException
from src.education_ai_system.services.pinecone_service import VectorizationService
from  src.education_ai_system.tools.pinecone_exa_tools import PineconeRetrievalTool
import os

router = APIRouter()

# # !!! make sure you remove before moving to production
@router.post("/clear-index-test")
async def clear_index():
    """Temporary route to clear index for testing"""
    retrieval_tool = PineconeRetrievalTool()
    retrieval_tool.clear_index_for_testing()
    return {"message": "Index cleared successfully"}

@router.post("/process_pdf")
async def process_pdf(file: UploadFile = File(...), country: str = Form(default="nigeria")):
    """
    This method will be used to prepocess your document by extracting text and tables from pdf document
    and stores it in the vector database 
    """
    try:
        #get the file name from the file that you upload
        file_path = f"temp_{file.filename}"
        #read the uploaded file
        with open(file_path, "wb") as f:
            #read the file in byte mode because it's not a text
            f.write(await file.read())
        
        service = VectorizationService(country=country) #the pinecone object that's used to stored the extracted pdf document
        #use the vectorizationservice object to process the file
        result =service.process_and_store_pdf(file_path)



        
        os.remove(file_path)
        
       # ✅ Return the actual result
        if result.get("status") == "success":
            return {
                "status": "success", 
                "message": f"PDF processed and stored successfully. {result.get('chunks_stored', 0)} chunks stored.",
                "chunks_stored": result.get("chunks_stored", 0)
            }
        else:
            return {"status": "error", "message": result.get("message", "Unknown error")}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
@router.get("/debug-index")
async def debug_index():
    """Debug endpoint to check what's stored in Pinecone"""
    try:
        # Use the existing PineconeRetrievalTool to check contents
        retrieval_tool = PineconeRetrievalTool(country="nigeria")
        retrieval_tool.debug_index_contents()
        
        # Get index stats
        stats = retrieval_tool.index.describe_index_stats()
        total_vectors = stats.get('total_vector_count', 0)
        
        # Sample query to see what's stored
        sample_vector = [0.0] * 384
        response = retrieval_tool.index.query(
            vector=sample_vector,
            top_k=10,
            include_metadata=True
        )
        
        matches = response.get('matches', [])
        subjects_found = set()
        grade_levels_found = set()
        sample_matches = []
        
        for match in matches:
            metadata = match.get('metadata', {})
            subject = metadata.get('subject', 'Unknown')
            grade_level = metadata.get('grade_level', 'Unknown')
            content_preview = metadata.get('content', '')[:100]
            
            subjects_found.add(subject)
            grade_levels_found.add(grade_level)
            sample_matches.append({
                'subject': subject,
                'grade_level': grade_level,
                'content_preview': content_preview
            })
        
        return {
            "total_vectors": total_vectors,
            "subjects_found": list(subjects_found),
            "grade_levels_found": list(grade_levels_found),
            "sample_matches": sample_matches
        }
        
    except Exception as e:
        raise HTTPException(500, detail=f"Debug failed: {str(e)}")