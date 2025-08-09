import streamlit as st
import requests
from typing import Dict, Any

class ContentGenerator:
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url
    
    def generate_scheme(self, subject: str, grade_level: str, topic: str, country: str = "nigeria") -> Dict[str, Any]:
        """Generate scheme of work"""
        payload = {
            "subject": subject, 
            "grade_level": grade_level, 
            "topic": topic,
            "country": country  # Add country to payload
        }
        
        with st.spinner("Generating scheme of work..."):
            response = requests.post(f"{self.api_base_url}/api/content/scheme-of-work", json=payload)
            
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
            return None
    
    def generate_lesson_plan(self, scheme_id: str, week: int, limitations: str) -> Dict[str, Any]:
        """Generate lesson plan"""
        payload = {
            "scheme_of_work_id": scheme_id,
            "week": week,
            "limitations": limitations
        }
        
        with st.spinner("Generating lesson plan..."):
            response = requests.post(f"{self.api_base_url}/api/content/lesson-plan", json=payload)
            
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
            return None
    
    def generate_lesson_notes(self, scheme_id: str, lesson_plan_id: str, week: int, subject: str = "", grade_level: str = "", topic: str = "", teaching_method: str = "") -> Dict[str, Any]:
        """Generate lesson notes"""
        payload = {
            "scheme_of_work_id": scheme_id,
            "lesson_plan_id": lesson_plan_id,
            "week": week,
            "subject": subject,
            "grade_level": grade_level,
            "topic": topic,
            "teaching_method": teaching_method
        }
        
        with st.spinner("Generating lesson notes..."):
            response = requests.post(f"{self.api_base_url}/api/content/lesson-notes", json=payload)
            
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
            return None
    
    # def generate_exam(self, scheme_id: str, lesson_plan_id: str, lesson_notes_id: str, week: int, exam_duration: str = "2 hours", total_marks: int = 100) -> Dict[str, Any]:
    #     """Generate exam - minimal constraints for testing"""
    #     payload = {
    #         "scheme_of_work_id": scheme_id,
    #         "lesson_plan_id": lesson_plan_id,
    #         "lesson_notes_id": lesson_notes_id,
    #         "week": week,
    #         "exam_duration": exam_duration,
    #         "total_marks": total_marks
    #     }
        
    #     with st.spinner("Generating exam..."):
    #         response = requests.post(f"{self.api_base_url}/api/content/exam-generator", json=payload)
            
    #     if response.status_code == 200:
    #         return response.json()
    #     else:
    #         st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
    #         return None

    def generate_exam(self, scheme_id: str, exam_type: str = "quiz") -> Dict[str, Any]:
        """Generate exam using the new API format"""
        payload = {
            "scheme_of_work_id": scheme_id,
            "exam_type": exam_type
        }
        
        with st.spinner("Generating exam..."):
            response = requests.post(f"{self.api_base_url}/api/content/exam-generator", json=payload)
            
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
            return None
