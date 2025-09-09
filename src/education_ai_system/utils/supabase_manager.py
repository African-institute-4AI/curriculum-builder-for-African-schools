# src/education_ai_system/utils/supabase_manager.py
import os
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime
from src.education_ai_system.utils.subject_mapper import subject_mapper
from typing import Dict, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SupabaseManager")

load_dotenv()

class SupabaseManager:
    def __init__(self):
        logger.info("Initializing Supabase client")
        try:
            #creating a client variable of type Client using the create_client method of supabase manager
            #then pass on the url and api key stored in the environment variable
            self.client: Client = create_client(
                os.getenv("SUPABASE_URL"),
                os.getenv("SUPABASE_KEY")
            )
            logger.info("✅ Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase client: {str(e)}")
            raise
    
    # This methods saves the curriculum document converted to embedding uding pinecone into the database(superbase)
    def store_context(self, subject: str, grade_level: str, topic: str, context: str, country: str = "nigeria") -> str:
        """Stores curriculum context in the database."""

        # Normalize subject before storing
        normalized_subject = subject_mapper.normalize_subject(subject)

        # logger.info(f"Storing context for {subject} ({grade_level}) - {topic} - Country: {country}")
        logger.info(f"Storing context for {normalized_subject} ({grade_level}) - {topic} - Country: {country}")
        try:
            #this line uses the supabase client instance to access the table in the database called 'curriculum_contex'
            #then use insert to add new row with the corrresponding dictionary values (like: subject: subject) etc
            result = self.client.table('curriculum_context').insert({
            "subject": normalized_subject,  # ← Now uses normalized subject!
            "grade_level": grade_level,
            "topic": topic,
            "country": country,
            "context": context
            }).execute()
            
            if result.data:
                context_id = result.data[0]['id']
                logger.info(f"✅ Context stored successfully. ID: {context_id}")
                return context_id
            logger.error("❌ Context storage failed: No data returned")
            return None
        except Exception as e:
            logger.error(f"❌ Context storage error: {str(e)}")
            return None


    def get_context_by_id(self, context_id: str) -> dict:
        """This method will be used to get the context by id from the database"""
        logger.info(f"Fetching context with ID: {context_id}")
        try:
            #this line uses the supabase client instance to access the table in the database called 'curriculum_context'
            #then use select to get the row with the corresponding context_id
            #then execute the query
            result = self.client.table('curriculum_context').select("*").eq("id", context_id).execute()
            #if the result is not empty, then return the context data
            if result.data:
                context_data = result.data[0]
                logger.info(f"✅ Found context: ID={context_data['id']}")
                #this line will ensure that the context data has the required fields
                #if the field is not present, then set it to 'Unknown'
                #this will help prevent errors if the context data is not complete
                context_data.setdefault('subject', 'Unknown')
                context_data.setdefault('grade_level', 'Unknown')
                context_data.setdefault('topic', 'Unknown')
                context_data.setdefault('context', 'No context available')
                
                return context_data
            logger.warning("⚠️ Context not found")
            return None
        except Exception as e:
            logger.error(f"❌ Context fetch error: {str(e)}")
            return None

    # SCHEME OPERATIONS
    def create_scheme(self, data: dict) -> str:
        """
        This method will be used to create the scheme of work as vector embedding in the database (supabase)
        it will use the data dictionary passed to it from session_manager instance - which will using the method
        """
        logger.info("Creating new scheme")
        try:
            # Build scheme data with context_id if available
            scheme_data = {
                "payload": data.get("payload"),
                "content": data.get("content"),
                "created_at": datetime.now().isoformat()
            }
            
            # Add context_id if provided then use that to create the scheme data dictionary above
            if "context_id" in data:
                scheme_data["context_id"] = data["context_id"]
            
            #if not then create find a new table called schemes then insert the scheme data dict given above
            result = self.client.table('schemes').insert(scheme_data).execute()
            
            if result.data:
                scheme_id = result.data[0]['id']
                logger.info(f"✅ Scheme created. ID: {scheme_id}")
                return scheme_id
            logger.error("❌ Scheme creation failed: No data returned")
            return None
        except Exception as e:
            logger.error(f"❌ Scheme creation error: {str(e)}")
            return None

    def get_scheme(self, scheme_id: str) -> dict:
        """
        This method will be used to create the scheme table in the supabase database using the scheme_id given
        """
        logger.info(f"Fetching scheme with ID: {scheme_id}")
        try:
            result = self.client.table('schemes').select("*").eq("id", scheme_id).execute()
            if result.data:
                logger.info(f"✅ Found scheme: ID={result.data[0]['id']}")
                return result.data[0]
            logger.warning("⚠️ Scheme not found")
            return None
        except Exception as e:
            logger.error(f"❌ Scheme fetch error: {str(e)}")
            return None

    def get_scheme_by_context(self, context_id: str) -> dict:
        logger.info(f"Fetching scheme by context ID: {context_id}")
        try:
            result = self.client.table('schemes').select("*").eq("context_id", context_id).execute()
            if result.data:
                scheme_id = result.data[0]['id']
                logger.info(f"✅ Found scheme: ID={scheme_id} for context {context_id}")
                return result.data[0]
            logger.warning("⚠️ Scheme not found for given context")
            return None
        except Exception as e:
            logger.error(f"❌ Scheme by context fetch error: {str(e)}")
            return None

    # LESSON PLAN OPERATIONS - UPDATED WITH WEEK FIELD
    def create_lesson_plan(self, scheme_id: str, data: dict) -> str:
        """
        This method will be used by session manager to create the lesson plan table in the supabase database
        """
        logger.info(f"Creating lesson plan for scheme ID: {scheme_id}")
        try:
            if not scheme_id:
                raise ValueError("Scheme ID is required")
            
            required_fields = ["payload", "content"]
            if not all(field in data for field in required_fields):
                raise ValueError("Missing required fields in lesson plan data")
            
            # Prepare the data to be inserted
            insert_data = {
                "scheme_id": scheme_id,
                "payload": data["payload"],
                "content": data["content"]
            }
            
            # Add week only if column exists
            if hasattr(self, '_week_column_exists') and self._week_column_exists:
                insert_data["week"] = data.get("week", "1")
            
            # Check if "context_id" is in the data and include it
            if "context_id" in data:
                insert_data["context_id"] = data["context_id"]
            
            # Insert the data into the table
            response = self.client.table('lesson_plans').insert(insert_data).execute()
            
            if response.data:
                plan_id = response.data[0]['id']
                logger.info(f"✅ Lesson plan created. ID: {plan_id}")
                return plan_id
            logger.error("❌ Lesson plan creation failed: No data returned")
            return None
        except Exception as e:
            # Handle missing week column specifically
            if "Could not find the 'week' column" in str(e):
                logger.warning("⚠️ 'week' column not found. Creating without week information")
                self._week_column_exists = False
                return self.create_lesson_plan(scheme_id, data)  # Retry without week
            logger.error(f"❌ Lesson plan creation error: {str(e)}")
            return None

    def get_lesson_plan(self, lesson_plan_id: str) -> dict:
        """
        This method will retrieve the lesson plan table created in the database
        """
        logger.info(f"Fetching lesson plan with ID: {lesson_plan_id}")
        try:
            result = self.client.table('lesson_plans').select("*").eq("id", lesson_plan_id).execute()
            if result.data:
                logger.info(f"✅ Found lesson plan: ID={result.data[0]['id']}")
                return result.data[0]
            logger.warning("⚠️ Lesson plan not found")
            return None
        except Exception as e:
            logger.error(f"❌ Lesson plan fetch error: {str(e)}")
            return None

    def get_lesson_plan_by_context(self, context_id: str) -> dict:
        logger.info(f"Fetching lesson plan by context ID: {context_id}")
        try:
            result = self.client.table('lesson_plans').select("*").eq("context_id", context_id).execute()
            if result.data:
                plan_id = result.data[0]['id']
                logger.info(f"✅ Found lesson plan: ID={plan_id} for context {context_id}")
                return result.data[0]
            logger.warning("⚠️ Lesson plan not found for given context")
            return None
        except Exception as e:
            logger.error(f"❌ Lesson plan by context fetch error: {str(e)}")
            return None

    # LESSON NOTES OPERATIONS - UPDATED WITH WEEK FIELD
    def create_lesson_notes(self, scheme_id: str, lesson_plan_id: str, data: dict) -> str:
        """
        This method will be used by session manager to create the lesson note table in the supabase database
        """
        logger.info(f"Creating lesson notes for scheme: {scheme_id}, plan: {lesson_plan_id}")
        try:
            # Check if scheme_id and lesson_plan_id are provided
            if not all([scheme_id, lesson_plan_id]):
                raise ValueError("Both scheme ID and lesson plan ID are required")
            
            # Ensure required fields are present in data
            required_fields = ["payload", "content"]
            if not all(field in data for field in required_fields):
                raise ValueError("Missing required fields in lesson notes data")
            
            # Build the data to be inserted, including context_id if provided
            insert_data = {
                "scheme_id": scheme_id,
                "lesson_plan_id": lesson_plan_id,
                "payload": data["payload"],
                "content": data["content"],
                "week": data.get("week", "1")  # Add week field with default
            }
            
            # Add context_id if provided
            if "context_id" in data:
                insert_data["context_id"] = data["context_id"]
            
            # Insert the lesson notes into the table
            response = self.client.table('lesson_notes').insert(insert_data).execute()
            
            if response.data:
                notes_id = response.data[0]['id']
                logger.info(f"✅ Lesson notes created. ID: {notes_id}")
                return notes_id
            logger.error("❌ Lesson notes creation failed: No data returned")
            return None
        except Exception as e:
            logger.error(f"❌ Lesson notes creation error: {str(e)}")
            return None

    def get_lesson_notes(self, notes_id: str) -> dict:
        """
        This method will retrieve the lesson note table created in the database
        """
        logger.info(f"Fetching lesson notes with ID: {notes_id}")
        try:
            result = self.client.table('lesson_notes').select("*").eq("id", notes_id).execute()
            if result.data:
                logger.info(f"✅ Found lesson notes: ID={result.data[0]['id']}")
                return result.data[0]
            logger.warning("⚠️ Lesson notes not found")
            return None
        except Exception as e:
            logger.error(f"❌ Lesson notes fetch error: {str(e)}")
            return None

    def get_lesson_notes_by_context(self, context_id: str) -> dict:
        logger.info(f"Fetching lesson notes by context ID: {context_id}")
        try:
            result = self.client.table('lesson_notes').select("*").eq("context_id", context_id).execute()
            if result.data:
                notes_id = result.data[0]['id']
                logger.info(f"✅ Found lesson notes: ID={notes_id} for context {context_id}")
                return result.data[0]
            logger.warning("⚠️ Lesson notes not found for given context")
            return None
        except Exception as e:
            logger.error(f"❌ Lesson notes by context fetch error: {str(e)}")
            return None


# EXAM OPERATIONS - NEW METHODS
    # def create_exam(self, scheme_id: str, lesson_plan_id: str, lesson_notes_id: str, data: dict) -> str:
    #     """
    #     This method will be used by session manager to create new exam record table in the supabase database
    #     """
    #     logger.info(f"Creating exam for scheme: {scheme_id}, plan: {lesson_plan_id}, notes: {lesson_notes_id}")
    #     try:
    #         # Validate required parameters
    #         if not all([scheme_id, lesson_plan_id, lesson_notes_id]):
    #             raise ValueError("Scheme ID, lesson plan ID, and lesson notes ID are all required")
            
    #         # Ensure required fields are present in data
    #         required_fields = ["payload", "content"]
    #         if not all(field in data for field in required_fields):
    #             raise ValueError("Missing required fields in exam data")
            
    #         # Build the data to be inserted
    #         insert_data = {
    #             "scheme_id": scheme_id,
    #             "lesson_plan_id": lesson_plan_id,
    #             "lesson_notes_id": lesson_notes_id,
    #             "payload": data["payload"],
    #             "content": data["content"],
    #             "week": data.get("week", "1"),  # Add week field with default
    #             "created_at": datetime.now().isoformat()
    #         }
            
    #         # Add context_id if provided
    #         if "context_id" in data:
    #             insert_data["context_id"] = data["context_id"]
            
    #         # Insert the exam into the table
    #         response = self.client.table('exams').insert(insert_data).execute()
            
    #         if response.data:
    #             exam_id = response.data[0]['id']
    #             logger.info(f"✅ Exam created. ID: {exam_id}")
    #             return exam_id
    #         logger.error("❌ Exam creation failed: No data returned")
    #         return None
    #     except Exception as e:
    #         logger.error(f"❌ Exam creation error: {str(e)}")
    #         return None

    def create_exam(self, scheme_id: str, lesson_plan_id: str, lesson_notes_id: str, data: dict) -> str:
        """Create exam - allow None for lesson_plan_id and lesson_notes_id for multi-week exams"""
        logger.info(f"Creating exam for scheme: {scheme_id}, plan: {lesson_plan_id}, notes: {lesson_notes_id}")
        try:
            # Only validate scheme_id is required
            if not scheme_id:
                raise ValueError("Scheme ID is required")
            
            # Ensure required fields are present in data
            required_fields = ["payload", "content"]
            if not all(field in data for field in required_fields):
                raise ValueError("Missing required fields in exam data")
            
            # Build the data to be inserted
            insert_data = {
                "scheme_id": scheme_id,
                "payload": data["payload"],
                "content": data["content"],
                "created_at": datetime.now().isoformat()
            }
            
            # Add lesson_plan_id and lesson_notes_id only if they are not None
            if lesson_plan_id:
                insert_data["lesson_plan_id"] = lesson_plan_id
            if lesson_notes_id:
                insert_data["lesson_notes_id"] = lesson_notes_id
            
            # Add context_id if provided
            if "context_id" in data:
                insert_data["context_id"] = data["context_id"]
            
            # Insert the exam into the table
            response = self.client.table('exams').insert(insert_data).execute()
            
            if response.data:
                exam_id = response.data[0]['id']
                logger.info(f"✅ Exam created. ID: {exam_id}")
                return exam_id
            logger.error("❌ Exam creation failed: No data returned")
            return None
        except Exception as e:
            logger.error(f"❌ Exam creation error: {str(e)}")
        return None

    def get_exam(self, exam_id: str) -> dict:
        """
        This method will retrieve an exam record by ID table created in the database
        """
        logger.info(f"Fetching exam with ID: {exam_id}")
        try:
            result = self.client.table('exams').select("*").eq("id", exam_id).execute()
            if result.data:
                logger.info(f"✅ Found exam: ID={result.data[0]['id']}")
                return result.data[0]
            logger.warning("⚠️ Exam not found")
            return None
        except Exception as e:
            logger.error(f"❌ Exam fetch error: {str(e)}")
            return None

    def get_exam_by_context(self, context_id: str) -> dict:
        """Retrieves an exam record by context ID."""
        logger.info(f"Fetching exam by context ID: {context_id}")
        try:
            result = self.client.table('exams').select("*").eq("context_id", context_id).execute()
            if result.data:
                exam_id = result.data[0]['id']
                logger.info(f"✅ Found exam: ID={exam_id} for context {context_id}")
                return result.data[0]
            logger.warning("⚠️ Exam not found for given context")
            return None
        except Exception as e:
            logger.error(f"❌ Exam by context fetch error: {str(e)}")
            return None

    def get_exams_by_scheme(self, scheme_id: str) -> list:
        """Retrieves all exams for a specific scheme."""
        logger.info(f"Fetching exams for scheme ID: {scheme_id}")
        try:
            result = self.client.table('exams').select("*").eq("scheme_id", scheme_id).execute()
            if result.data:
                logger.info(f"✅ Found {len(result.data)} exams for scheme {scheme_id}")
                return result.data
            logger.warning("⚠️ No exams found for given scheme")
            return []
        except Exception as e:
            logger.error(f"❌ Exams by scheme fetch error: {str(e)}")
            return []

    def get_exams_by_lesson_plan(self, lesson_plan_id: str) -> list:
        """Retrieves all exams for a specific lesson plan."""
        logger.info(f"Fetching exams for lesson plan ID: {lesson_plan_id}")
        try:
            result = self.client.table('exams').select("*").eq("lesson_plan_id", lesson_plan_id).execute()
            if result.data:
                logger.info(f"✅ Found {len(result.data)} exams for lesson plan {lesson_plan_id}")
                return result.data
            logger.warning("⚠️ No exams found for given lesson plan")
            return []
        except Exception as e:
            logger.error(f"❌ Exams by lesson plan fetch error: {str(e)}")
            return []

    def get_exams_by_lesson_notes(self, lesson_notes_id: str) -> list:
        """Retrieves all exams for specific lesson notes."""
        logger.info(f"Fetching exams for lesson notes ID: {lesson_notes_id}")
        try:
            result = self.client.table('exams').select("*").eq("lesson_notes_id", lesson_notes_id).execute()
            if result.data:
                logger.info(f"✅ Found {len(result.data)} exams for lesson notes {lesson_notes_id}")
                return result.data
            logger.warning("⚠️ No exams found for given lesson notes")
            return []
        except Exception as e:
            logger.error(f"❌ Exams by lesson notes fetch error: {str(e)}")
            return []

    def update_exam(self, exam_id: str, data: dict) -> bool:
        """Updates an existing exam record."""
        logger.info(f"Updating exam with ID: {exam_id}")
        try:
            # Prepare update data
            update_data = {}
            
            # Only include fields that are present in the data
            updatable_fields = ["payload", "content", "week"]
            for field in updatable_fields:
                if field in data:
                    update_data[field] = data[field]
            
            # Add updated timestamp
            update_data["updated_at"] = datetime.now().isoformat()
            
            if not update_data:
                logger.warning("⚠️ No valid fields to update")
                return False
            
            # Update the exam
            response = self.client.table('exams').update(update_data).eq("id", exam_id).execute()
            
            if response.data:
                logger.info(f"✅ Exam updated successfully. ID: {exam_id}")
                return True
            logger.error("❌ Exam update failed: No data returned")
            return False
        except Exception as e:
            logger.error(f"❌ Exam update error: {str(e)}")
            return False

    def delete_exam(self, exam_id: str) -> bool:
        """Deletes an exam record."""
        logger.info(f"Deleting exam with ID: {exam_id}")
        try:
            response = self.client.table('exams').delete().eq("id", exam_id).execute()
            
            if response.data:
                logger.info(f"✅ Exam deleted successfully. ID: {exam_id}")
                return True
            logger.error("❌ Exam deletion failed: No data returned")
            return False
        except Exception as e:
            logger.error(f"❌ Exam deletion error: {str(e)}")
            return False
        
    def get_lesson_plans_by_scheme(self, scheme_id: str) -> list:
        """Retrieves all lesson plans for a specific scheme."""
        logger.info(f"Fetching lesson plans for scheme ID: {scheme_id}")
        try:
            result = self.client.table('lesson_plans').select("*").eq("scheme_id", scheme_id).execute()
            if result.data:
                logger.info(f"✅ Found {len(result.data)} lesson plans for scheme {scheme_id}")
                return result.data
            logger.warning("⚠️ No lesson plans found for given scheme")
            return []
        except Exception as e:
            logger.error(f"❌ Lesson plans by scheme fetch error: {str(e)}")
            return []

    def get_lesson_notes_by_scheme(self, scheme_id: str) -> list:
        """Retrieves all lesson notes for a specific scheme."""
        logger.info(f"Fetching lesson notes for scheme ID: {scheme_id}")
        try:
            result = self.client.table('lesson_notes').select("*").eq("scheme_id", scheme_id).execute()
            if result.data:
                logger.info(f"✅ Found {len(result.data)} lesson notes for scheme {scheme_id}")
                return result.data
            logger.warning("⚠️ No lesson notes found for given scheme")
            return []
        except Exception as e:
            logger.error(f"❌ Lesson notes by scheme fetch error: {str(e)}")
            return []