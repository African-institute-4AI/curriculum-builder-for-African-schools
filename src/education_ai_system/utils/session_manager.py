# src/education_ai_system/utils/session_manager.py

#we want to use superbase manager file in session_manager.py file
from .supabase_manager import SupabaseManager

class SessionManager:
    def __init__(self):
        #create the object of SupabaseManager class to be used as class attribute (class instance or class variable)
        self.supabase = SupabaseManager()
        self.current_scheme_id = None
        self.current_lesson_plan_id = None
        self.current_lesson_notes_id = None

    # Scheme Operations
    def create_scheme(self, data: dict) -> str:
        """
        This method will use its instance supabase (which is also linked with the supabaseManager class) to get 
        the create_scheme method from the supabaseManager and create the table in the database
        """
        scheme_id = self.supabase.create_scheme(data)
        self.current_scheme_id = scheme_id
        return scheme_id

    def get_scheme(self, scheme_id: str) -> dict:
        """will use the get_scheme method of the supabase manager class to get the schema table from the database"""
        return self.supabase.get_scheme(scheme_id)

    # Lesson Plan Operations - UPDATED WITH WEEK FIELD
    def create_lesson_plan(self, scheme_id: str, data: dict) -> str:
        """
        This method will use its instance supabase (which is also linked with the supabaseManager class) to get 
        the create_lesson plan method from the supabaseManager and create the table in the database
        """
        # Ensure week is present in data
        if "week" not in data:
            data["week"] = "1"
        
        lesson_plan_id = self.supabase.create_lesson_plan(scheme_id, data)
        self.current_lesson_plan_id = lesson_plan_id
        return lesson_plan_id

    def get_lesson_plan(self, lesson_plan_id: str) -> dict:
        """
        This method will retrieve the lesson plan table created in the database 
        """
        return self.supabase.get_lesson_plan(lesson_plan_id)

    # Lesson Notes Operations - UPDATED WITH WEEK FIELD
    def create_lesson_notes(self, scheme_id: str, lesson_plan_id: str, data: dict) -> str:
        """
        This method will use its instance supabase (which is also linked with the supabaseManager class) to get 
        the create_lesson notes method from the supabaseManager and create the table in the database
        """
        # Ensure week is present in data
        if "week" not in data:
            data["week"] = "1"
        
        notes_id = self.supabase.create_lesson_notes(scheme_id, lesson_plan_id, data)
        self.current_lesson_notes_id = notes_id
        return notes_id

    def get_lesson_notes(self, notes_id: str) -> dict:
        """
        This method will retrieve the lesson note table created in the database 
        """
        return self.supabase.get_lesson_notes(notes_id)
    
    def create_exam(self, scheme_id: str, lesson_plan_id: str, lesson_notes_id: str, data: dict) -> str:
        """
        This method will use its instance supabase (which is also linked with the supabaseManager class) to get 
        the create_exam  method from the supabaseManager and create the table in the database
        """
        exam_id = self.supabase.create_exam(scheme_id, lesson_plan_id, lesson_notes_id, data)
        return exam_id

    def get_exam(self, exam_id: str) -> dict:
        """
        This method will retrieve the exam table created in the database 
        """
        return self.supabase.get_exam(exam_id)