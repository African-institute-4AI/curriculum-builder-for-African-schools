# src/education_ai_system/tools/pinecone_exa_tools.py

from langchain.tools import BaseTool
import os
import json
import torch
import re
from transformers import AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer
from pydantic import Field, ConfigDict
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from pinecone import Pinecone
import pinecone
from src.education_ai_system.utils.subject_mapper import subject_mapper
from src.education_ai_system.utils.validators import validate_user_input

# Load environment variables
load_dotenv()

# ✅ Global variables for memory efficiency
tokenizer = None
model = None

def get_model():
    global model
    if model is None:
        print("🔄 Loading embedding model...")
        # model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        # ✅ Force CPU usage for deployment
        model.eval()  # Set to evaluation mode
        print("✅ Model loaded successfully")
    return model

def get_tokenizer():
    global tokenizer
    if tokenizer is None:
        print("🔄 Loading tokenizer...")
        # tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
        tokenizer = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        print("✅ Tokenizer loaded successfully")
    return tokenizer

#this class inherite from the abstract class BaseTool 
#that defines all the interface that all langchain too must implement
class PineconeRetrievalTool(BaseTool):
    """Tool to retrieve relevant context from Pinecone vector database based on user query."""
    index: Optional[Any] = Field(default=None)  # Simplified type hint
    pc: Optional[Any] = Field(default=None)  # Pinecone client field
    stored_context: Optional[str] = None  # Store context for future use
    country: str = Field(default="nigeria")  # Add country field
    
    # Updated Pydantic config (v2 style)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, country: str = "nigeria", **kwargs):
        # Initialize the tool FIRST
        name = "Pinecone Retrieval Tool"
        description = (
            f"Fetches context from Pinecone for {country.title()}. Accepts JSON input with keys: "
            "'subject', 'grade_level', 'topic'"
        )
        #You have to initialize the superclass (BaseTool) because its inheriting from 
        #an abstract class 
        super().__init__(name=name, description=description, **kwargs)

        # Initialize Pinecone client AFTER super()
        api_key = os.getenv("PINECONE_API_KEY")
        # get its index name
        index_name = os.getenv("PINECONE_INDEX")
        
        if not api_key:
            raise ValueError("Error: Pinecone API key is missing. Check your environment variables.")
        #get the pinecone class and pass the pinecone api
        #to create the pinecone object (instance)
        self.pc = Pinecone(api_key=api_key)

        # Initialize Pinecone index
        try:
            # Use Pinecone instance to list and create index if needed
            #first obtain the available indexes
            available_indexes = self.pc.list_indexes().names()
            #create a new index if not available
            if index_name not in available_indexes:
                print(f"Index '{index_name}' does not exist. Creating it now...")
                #cloud location of the index
                spec = pinecone.ServerlessSpec(cloud="aws", region="us-east-1")
                #this code creates a pincode index to store educational material
                #converting educational document to vector
                self.pc.create_index(
                    name=index_name,
                    dimension=384, #vector
                    metric="cosine", #similarity measure
                    spec=spec #storeage location
                )
                print(f"Index '{index_name}' created successfully.")
            #but if an index name is already in pinecone database
            else:
                print(f"Index '{index_name}' found.")
            #create the index
            self.index = self.pc.Index(index_name)
            print(f"Successfully connected to Pinecone index: {index_name}")
        except Exception as e:
            print(f"Error initializing Pinecone index '{index_name}': {e}")
            self.index = None

    # Add this temporary method to your PineconeRetrievalTool for testing
    #!!! This method should be remove in production
    def clear_index_for_testing(self):
        """Temporary method to clear index for testing"""
        try:
            # Delete all vectors (be careful!)
            self.index.delete(delete_all=True)
            print("✅ Index cleared successfully")
        except Exception as e:
            print(f"❌ Error clearing index: {e}")
            
    def _parse_query(self, query: str) -> Optional[Dict[str, str]]:
        """Parses a plain string query into a structured dictionary"""
        parts = query.split(",")
        if len(parts) != 3:
            return None
        return {
            "subject": parts[0].strip().lower(),
            "grade_level": parts[1].strip().lower(),
            "topic": parts[2].strip().lower()
        }
    def _grade_matches(self, user_grade: str, stored_grade: str) -> bool:
        """Smart grade matching that handles ranges"""
        print(f"🔍 Checking: user='{user_grade}' vs stored='{stored_grade}'")
        
        # Exact match
        if user_grade == stored_grade:
            print("✅ Exact match")
            return True
        
        # Extract user grade number
        user_num = self._extract_grade_number(user_grade)
        if user_num is None:
            print("❌ Could not extract user grade number")
            return False
        
        # Check if stored grade is a range
        if "-" in stored_grade:
            start_num, end_num = self._extract_grade_range(stored_grade)
            if start_num and end_num:
                match = start_num <= user_num <= end_num
                print(f"📊 Range check: {start_num} <= {user_num} <= {end_num} = {match}")
                return match
        else:
            # Single grade comparison
            stored_num = self._extract_grade_number(stored_grade)
            if stored_num:
                match = user_num == stored_num
                print(f"🎯 Single grade: {user_num} == {stored_num} = {match}")
                return match
        
        print("❌ No match found")
        return False
    def _extract_grade_number(self, grade_text: str) -> int:
        """Extract grade number from text like 'primary four' or 'primary 4'"""
        grade_text = grade_text.lower().strip()
        
        # Word to number mapping
        word_to_num = {
            "one": 1, "two": 2, "three": 3, "four": 4, 
            "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9
        }
        
        # Try to find number directly
        numbers = re.findall(r'\d+', grade_text)
        if numbers:
            return int(numbers[0])
        
        # Try word mapping
        for word, num in word_to_num.items():
            if word in grade_text:
                return num
        
        return None
    def _extract_grade_range(self, grade_text: str) -> tuple:
        """Extract start and end numbers from range like 'primary 4-6'"""
        numbers = re.findall(r'\d+', grade_text)
        if len(numbers) >= 2:
            return int(numbers[0]), int(numbers[1])
        return None, None


   

    def _run(self, query: str) -> str:
        """Runs the tool with JSON input"""
        try:
            # Parse the JSON input directly
            parsed_query = json.loads(query)
            # Perform validation and retrieval
            result = self._validate_and_retrieve(parsed_query)
            return json.dumps(result, indent=2)
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "message": "Query must be JSON with keys: subject, grade_level, topic"
            })
        except Exception as e:
            return json.dumps({"status": "error", "message": f"Unexpected error: {str(e)}"})

    

    def _validate_and_retrieve(self, query: Dict[str, str], num_results: int = 10) -> Dict:
        """Validates the query and retrieves context from Pinecone"""
        
        # FIRST: Check if index has any data
        try:
            stats = self.index.describe_index_stats()
            total_vectors = stats.get('total_vector_count', 0)
            print(f"📊 TOTAL VECTORS IN INDEX: {total_vectors}")
            
            if total_vectors == 0:
                return {
                    "status": "error",
                    "message": "Pinecone index is EMPTY. Please upload a PDF document first using the upload endpoint."
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error checking index: {str(e)}"
            }

        # Validate query format
        required_keys = ['subject', 'grade_level', 'topic']
        if not all(key in query for key in required_keys):
            return {
                "status": "error",
                "message": f"Query must contain keys: {required_keys}"
            }

        # Normalize subject using subject mapper
        normalized_subject = subject_mapper.normalize_subject(query['subject'])
        query['subject'] = normalized_subject

        print(f"🔍 Searching for: subject='{query['subject']}', grade='{query['grade_level']}', topic='{query['topic']}'")

        # Create query text for embedding
        user_query_text = f"{query['subject']} {query['grade_level']} {query['topic']}"
        query_vector = self._get_query_embedding(user_query_text)

        # Query Pinecone with COUNTRY and SUBJECT filters
        try:
            if not self.index:
                raise ValueError("Pinecone index is not initialized.")
            
            # Search with both country and subject filters
            response = self.index.query(
                vector=query_vector,
                top_k=30,  # ✅ Increased from 20 to 30
                include_metadata=True,
                filter={
                    "$and": [
                        {"country": {"$eq": self.country}},
                        {"subject": {"$eq": query['subject']}}
                    ]
                }
            )

            matches = response.get("matches", [])
            print(f"�� Found {len(matches)} matches for subject '{query['subject']}'")
            
            # Filter by grade using your smart matching
            filtered_matches = []
            for match in matches:
                stored_grade = match["metadata"].get("grade_level", "")
                if self._grade_matches(query['grade_level'], stored_grade):
                    filtered_matches.append(match)
            
            print(f"✅ {len(filtered_matches)} matches after grade filtering")
            
            # ✅ NEW: Filter by topic relevance
            topic_filtered_matches = []
            topic_keywords = query['topic'].lower().split()
            
            for match in filtered_matches:
                content = match["metadata"].get("content", "").lower()
                topics = match["metadata"].get("topics", [])
                
                # Check if topic keywords appear in content or topics
                topic_relevance = 0
                for keyword in topic_keywords:
                    if keyword in content:
                        topic_relevance += 1
                    for topic in topics:
                        if keyword in topic.lower():
                            topic_relevance += 2  # Higher weight for topic matches
                
                if topic_relevance > 0:
                    match["topic_relevance"] = topic_relevance
                    topic_filtered_matches.append(match)
            
            # Sort by topic relevance, then by score
            topic_filtered_matches.sort(key=lambda x: (x.get("topic_relevance", 0), x.get("score", 0)), reverse=True)
            
            print(f"🎯 {len(topic_filtered_matches)} matches after topic filtering")
            
            final_matches = topic_filtered_matches[:num_results]

            if not final_matches:
                return {"status": "invalid", "message": "No relevant data found.", "alternatives": []}

            # Build context from top matches
            context = "\n\n".join([
                match["metadata"].get("content", "")
                for match in final_matches
            ])
            
            # Store context for future use
            self.stored_context = context

            # Prepare matches in a serializable format
            serializable_matches = [
                {
                    "id": match["id"],
                    "score": match["score"],
                    "topic_relevance": match.get("topic_relevance", 0),
                    "metadata": match["metadata"]
                }
                for match in final_matches
            ]

            return {
                "status": "valid",
                "context": context,
                "matches": serializable_matches,
                "alternatives": []
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error querying Pinecone: {str(e)}"
            }

    

    def _get_query_embedding(self, text: str) -> List[float]:
        """Generates embeddings for a query text"""
        # Initialize tokenizer and model for embeddings
        tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
        model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
        with torch.no_grad():
            query_embedding = model(**inputs).last_hidden_state.mean(dim=1).cpu().numpy().squeeze()
        return query_embedding.tolist()

    def debug_index_contents(self):
        """Debug method to check index contents and statistics"""
        try:
            if not self.index:
                print("❌ Index is not initialized")
                return
                
            # Get index stats
            stats = self.index.describe_index_stats()
            print(f"📊 Index Stats: {stats}")
            
            # Try a sample query to see what subjects are actually stored
            sample_vector = [0.0] * 384  # Create a zero vector with correct dimensions
            response = self.index.query(
                vector=sample_vector,
                top_k=10,  # Get more samples
                include_metadata=True
            )
            
            print(f"🔍 Sample query returned {len(response.get('matches', []))} matches")
            
            if response.get('matches'):
                print("📝 What's actually stored in the index:")
                subjects_found = set()
                grade_levels_found = set()
                
                for i, match in enumerate(response['matches'][:10]):  # Show first 10 matches
                    metadata = match.get('metadata', {})
                    subject = metadata.get('subject', 'Unknown')
                    grade_level = metadata.get('grade_level', 'Unknown')
                    content_preview = metadata.get('content', '')[:100]
                    
                    subjects_found.add(subject)
                    grade_levels_found.add(grade_level)
                    
                    print(f"  Match {i+1}: Subject='{subject}', Grade='{grade_level}'")
                    print(f"    Content preview: {content_preview}...")
                    print(f"    Score: {match.get('score', 'N/A')}")
                    print("---")
                
                print(f"🎯 Unique subjects found in index: {sorted(subjects_found)}")
                print(f"🎯 Unique grade levels found in index: {sorted(grade_levels_found)}")
            else:
                print("⚠️  No matches found - index might be empty")
                
        except Exception as e:
            print(f"❌ Error in debug_index_contents: {e}")
# Rebuild the model to resolve Pydantic's forward references
PineconeRetrievalTool.model_rebuild()