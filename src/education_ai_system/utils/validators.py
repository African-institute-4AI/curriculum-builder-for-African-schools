import yaml
from typing import Dict, Optional
import os
from pathlib import Path
import json
import re
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from src.education_ai_system.embeddings.pinecone_manager import PineconeManager

load_dotenv()


def parse_query(query: str) -> Optional[Dict[str, str]]:
    """
    Parses a plain string query into a structured dictionary.
    Args:
        query (str): Plain string query in the format 'subject, grade_level, topic'.
    Returns:
        dict: Parsed query with 'subject', 'grade_level', and 'topic' keys, or None if parsing fails.
    """
    parts = query.split(",")
    if len(parts) != 3:
        return None

    return {
        "subject": parts[0].strip().lower(),
        "grade_level": parts[1].strip().lower(),
        "topic": parts[2].strip().lower()
    }



def validate_user_input(query: Dict[str, str]) -> bool:
    """Simple validation - let Pinecone search handle the matching"""
    # Basic format validation
    required_fields = ['subject', 'grade_level', 'topic']
    
    for field in required_fields:
        if not query.get(field) or not query[field].strip():
            print(f"Missing or empty field: {field}")
            return False
    
    print(f"Query format valid: {query}")
    return True  # Let Pinecone search determine if content exists
    



def extract_weeks_from_scheme(scheme_content: str) -> list:
    """Robust week extraction from scheme content"""
    weeks = []
    
    # Method 1: Table-based extraction
    for line in scheme_content.split('\n'):
        if '|' in line:
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if parts and parts[0].isdigit():
                weeks.append(parts[0])
    
    # Method 2: Pattern-based extraction
    if not weeks:
        import re
        week_pattern = r'\bweek\s*(\d+)\b|\b(\d+)\b'
        matches = re.findall(week_pattern, scheme_content, re.IGNORECASE)
        for match in matches:
            week_num = match[0] or match[1]  # Handle different capture groups
            if week_num not in weeks:
                weeks.append(week_num)
    
    # Ensure we have at least week 1
    if not weeks:
        weeks = ["1"]
    
    return sorted(weeks, key=int)

def extract_week_topic(scheme_content: str, week: str) -> str:
    """Extract topic for a specific week from scheme content using the best parsing method to extract it"""
    # Normalize week format by removing any non-digit characters - get the week number (in first column fo the table)
    clean_week = ''.join(filter(str.isdigit, week))
    
    # First try: if the scheme content is stored as a table this line will be used to extract its topics
    for line in scheme_content.split('\n'):#turn the whole table into a list of lines and split the table at every new line
        
        #get the week number bounded by | |
        if f"| {clean_week} |" in line or f"|{clean_week}|" in line:
            #split the line into column where it sees "|", clean up white space 
            parts = [p.strip() for p in line.split('|') if p.strip()]
            #checks if the returned list above is a table (with at least 3 columns)
            if len(parts) >= 3:
                #return the second column 
                return parts[1]  # Topic column
    
    # Second try: second method to be used  - flexible pattern matching
    for line in scheme_content.split('\n'):
        #if the week number is in the list of line generated above
        if clean_week in line:
            # Look for topic after the week number - this will get the topic which is found in week number, first_column like (week 1, column 1)
            parts = line.split(clean_week, 1)
            #if we have one topic at least
            if len(parts) > 1:
                # Extract text after week number
                topic_part = parts[1].strip()
                # Remove any trailing table characters
                if '|' in topic_part:
                    topic_part = topic_part.split('|')[0]
                if topic_part:
                    return topic_part
    
    # Fallback: return the main topic if week-specific not found
    if "TOPIC:" in scheme_content:
        topic_line = [line for line in scheme_content.split('\n') if "TOPIC:" in line]
        if topic_line:
            return topic_line[0].split("TOPIC:")[1].strip()
    
    # Final fallback
    return "General Topic"

def extract_week_content(content: str, week: str) -> str:
    """Extract content for a specific week from markdown content"""
    week_header = f"WEEK {week}"
    start_index = content.find(week_header)
    if start_index == -1:
        return "" 
    
    end_index = content.find("WEEK ", start_index + len(week_header))
    if end_index == -1:
        return content[start_index:]  # Return remaining content if last week
    
    return content[start_index:end_index]

def load_prompt(prompt_name: str) -> str:
    """Load prompt template from YAML files"""
    prompt_path = Path(__file__).parent.parent / "config" / "prompts" / f"{prompt_name}.yaml"
    with open(prompt_path) as f:
        prompt_data = yaml.safe_load(f)
    return prompt_data['system_prompt'] + "\n\n" + prompt_data['user_prompt_template']