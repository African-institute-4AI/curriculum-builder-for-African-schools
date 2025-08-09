#from pinecone manager package import Pineconemanager class
import yaml
from src.education_ai_system.embeddings.pinecone_manager import PineconeManager
from src.education_ai_system.utils.subject_mapper import subject_mapper
from langchain.document_loaders import PyPDFLoader
from langchain_groq import ChatGroq
from pathlib import Path
import json
import re
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os



class VectorizationService:
    def __init__(self, country: str = "nigeria"):
        self.pinecone_manager = PineconeManager()
        self.country = country
        self.country_patterns = self._load_country_patterns()


    def _load_country_patterns(self):
        """Load country-specific patterns from config file"""
        config_path = Path(__file__).parent.parent / "config" / f"patterns_{self.country}.yaml"
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            print(f"⚠️ Pattern file for {self.country} not found, using Nigeria defaults")
            # Fallback to Nigeria patterns
            config_path = Path(__file__).parent.parent / "config" / "patterns_nigeria.yaml"
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)

    def process_and_store_pdf(self, pdf_path: str):
        # Load PDF using PyPDFLoader
        loader = PyPDFLoader(pdf_path)
        docs = loader.load()
        
        # Use AI to intelligently extract metadata from the document
        extracted_metadata = self._intelligent_metadata_extraction(docs)
        print(f"🤖 AI Extracted Metadata: {extracted_metadata}")
        
        # Use RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,  
            chunk_overlap=50
        )
        split_documents = text_splitter.split_documents(docs)
        
        # Prepare for Pinecone storage with intelligent metadata
        chunks = []
        metadata = []
        
        grade_topics = extracted_metadata.get("grade_topics", {})
        default_grade = extracted_metadata.get("grade_level", "unknown")
        
        for doc in split_documents:
            chunk_text = doc.page_content.lower()
            
            # Try to determine specific grade for this chunk
            specific_grade = self._determine_chunk_grade(chunk_text, grade_topics, default_grade)
            
            chunks.append(doc.page_content)
            metadata.append({
                "subject": extracted_metadata.get("subject", "general").lower(),
                "grade_level": specific_grade,
                "content": doc.page_content,
                "source": doc.metadata.get("source", "unknown"),
                "page": doc.metadata.get("page", 0),
                "document_type": extracted_metadata.get("document_type", "curriculum"),
                "topics": extracted_metadata.get("topics", [])
            })
        
        print(f"📊 Processed {len(chunks)} chunks with grade-specific metadata")
    
        # Store in Pinecone WITH COUNTRY
        self.pinecone_manager.upsert_content(chunks, metadata, country=self.country)

   
    def _determine_chunk_grade(self, chunk_text: str, grade_topics: dict, default_grade: str) -> str:
        """Determine the specific grade level for a text chunk based on topics"""
        
        # FIRST: Check grade-specific topics
        for grade, topics in grade_topics.items():
            for topic in topics:
                if topic.lower() in chunk_text:
                    print(f"🎯 Found topic '{topic}' → assigning grade '{grade}'")
                    return grade
        
        # SECOND: Use country-specific patterns
        grade_patterns = self.country_patterns.get('grade_patterns', [])
            
        for pattern in grade_patterns:
            matches = re.findall(pattern, chunk_text.lower())
            if matches:
                if len(matches[0]) == 2:  # Tuple like ('primary', '4')
                    level, num = matches[0]
                    standardized = f"{level} {num}"
                else:  # Single number - infer from context using country-specific keywords
                    num = matches[0]
                    standardized = self._infer_grade_level_from_context(chunk_text, num)
                
                print(f"🎯 Found explicit grade '{standardized}' in chunk")
                return standardized
        
        # FALLBACK: Preserve document-level range
        print(f"🔄 No specific grade found → using default '{default_grade}'")
        return default_grade
        
    def _infer_grade_level_from_context(self, chunk_text: str, grade_num: str) -> str:
        """Infer grade level using country-specific inference keywords"""
        chunk_lower = chunk_text.lower()
        inference_keywords = self.country_patterns.get('inference_keywords', {})
        number_ranges = self.country_patterns.get('number_ranges', {})
        
        # Try to match context keywords first
        for level, keywords in inference_keywords.items():
            if any(keyword in chunk_lower for keyword in keywords):
                return f"{level} {grade_num}"
        
        # Fallback: Use number ranges
        grade_int = int(grade_num)
        for level, num_range in number_ranges.items():
            if grade_int in num_range:
                return f"{level} {grade_num}"
        
        # Ultimate fallback
        return f"grade {grade_num}"
    
    def _intelligent_metadata_extraction(self, docs) -> dict:
        """Use AI to intelligently extract metadata from any curriculum document"""
        
        # Sample from beginning, middle, and end of document
        total_docs = len(docs)
        sample_indices = [0]  # Always include first page
        
        if total_docs > 2:
            sample_indices.append(total_docs // 2)  # Middle page
        if total_docs > 1:
            sample_indices.append(total_docs - 1)  # Last page
        
        # Get more comprehensive sample text
        sample_text = " ".join([docs[i].page_content for i in sample_indices])[:5000]  # Increased to 5000 chars

        # Get country-specific context for the prompt
        country_context = self._get_country_context()
        
        try:
            prompt = f"""
            Analyze this curriculum document text and extract the following information in JSON format:
            
            Text: {sample_text}
        
            Extract:
            1. subject: The main subject (e.g., {', '.join(country_context['subjects'][:5])}, etc.)
            2. grade_level: The grade level or range using {self.country.title()} terminology (e.g., {', '.join(country_context['grade_examples'])})
            3. document_type: Type of document (curriculum, syllabus, textbook, etc.)
            4. topics: List of main topics covered (max 10)
            
            IMPORTANT: 
            - Use {self.country.title()} education system terminology
            - Look for grade ranges like {country_context['range_examples'][0]} or {country_context['range_examples'][1]}
            - If you see multiple grades, include the full range
        
            
            Return ONLY a valid JSON object with these keys. If you cannot determine a value, use "unknown" for strings or [] for arrays.
            
            Example:
            {{
                "subject": "{country_context['subjects'][0]}",
                "grade_level": "{country_context['grade_examples'][0]}",
                "document_type": "curriculum",
                "topics": ["{country_context['sample_topics'][0]}", "{country_context['sample_topics'][1]}"]
            }}
            """
            
            llm = ChatGroq(
                temperature=0.1,
                model_name="llama3-70b-8192",
                max_tokens=500
            )
            
            response = llm.invoke([{"role": "user", "content": prompt}])
            ai_response = response.content.strip()
            
            print(f"🤖 Raw AI Response: {ai_response}")
        
            
            # Find JSON in the response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                metadata = json.loads(json_match.group())
            else:
                metadata = json.loads(ai_response)
            
            # Validate and clean the extracted data
            metadata = self._validate_and_clean_metadata(metadata)
            
            return metadata
            
        except Exception as e:
            print(f"AI extraction failed: {e}")
            # Fallback to simple text analysis
            return self._fallback_text_analysis(sample_text)


    def _get_country_context(self) -> dict:
        """Get country-specific context for LLM prompts"""
        llm_context = self.country_patterns.get('llm_context', {})
        subjects = self.country_patterns.get('subjects', ['mathematics', 'english', 'science'])
        
        return {
            "subjects": subjects,
            "grade_examples": llm_context.get('grade_examples', ["grade 4", "grade 4-6"]),
            "range_examples": llm_context.get('range_examples', ["Grade 4-6", "Grade 1-3"]),
            "sample_topics": llm_context.get('sample_topics', ["numbers", "algebra", "geometry"])
        }

    
    def _validate_and_clean_metadata(self, metadata: dict) -> dict:
        """Validate and standardize the extracted metadata"""

        # Use the shared subject mapper
        subject = metadata.get("subject", "unknown").lower().strip()

        # Normalize subject using subject_mapper (handles all variations)
        normalized_subject = subject_mapper.normalize_subject(subject)

        # STORE in normal format (spaces, not underscores)
        metadata["subject"] = normalized_subject

        # Standardize grade levels
        grade_level = metadata.get("grade_level", "unknown").lower().strip()
        metadata["grade_level"] = self._standardize_grade_level(grade_level)

        return metadata


    def _standardize_grade_level(self, grade_text: str) -> str:
        """Convert various grade formats to standard format for ALL levels"""
        grade_text = grade_text.lower()
        
        # Extract numbers from grade text
        numbers = re.findall(r'\d+', grade_text)
        if not numbers:
            return "unknown"
        
        # Handle ranges for any level
        if len(numbers) > 1:
            start_num = int(numbers[0])
            end_num = int(numbers[1])
            
            if "primary" in grade_text:
                return f"primary {start_num}-{end_num}"
            elif "secondary" in grade_text:
                return f"secondary {start_num}-{end_num}"
            elif "jss" in grade_text:
                return f"jss {start_num}-{end_num}"
            elif "sss" in grade_text:
                return f"sss {start_num}-{end_num}"
            else:
                return f"primary {start_num}-{end_num}"  # Default
        
        # Single grade - detect level
        grade_num = int(numbers[0])
        
        if "primary" in grade_text or "elementary" in grade_text:
            return f"primary {grade_num}"
        elif "secondary" in grade_text:
            return f"secondary {grade_num}"
        elif "jss" in grade_text:
            return f"jss {grade_num}"
        elif "sss" in grade_text:
            return f"sss {grade_num}"
        elif "tertiary" in grade_text or "university" in grade_text:
            return f"tertiary {grade_num}"
        else:
            # Infer based on number range
            if 1 <= grade_num <= 6:
                return f"primary {grade_num}"
            elif 7 <= grade_num <= 12:
                return f"secondary {grade_num}"
            else:
                return f"primary {grade_num}"  # Default

    def _fallback_text_analysis(self, text: str) -> dict:
        """Fallback method using simple text analysis if AI fails"""
        text_upper = text.upper()
        
        # Simple keyword matching as fallback
        subject = "general"
        if "MATHEMATICS" in text_upper or "MATH" in text_upper:
            subject = "mathematics"
        elif "ENGLISH" in text_upper:
            subject = "english"
        elif "SCIENCE" in text_upper:
            subject = "science"
        elif "CIVIC" in text_upper:
            subject = "civic education"
        
        # Simple grade extraction
        grade_level = "unknown"
        import re
        grade_matches = re.findall(r'PRIMARY\s+(\d+)', text_upper)
        if grade_matches:
            num = int(grade_matches[0])
            number_words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}
            grade_level = f"primary {number_words.get(num, str(num))}"
        
        return {
            "subject": subject,
            "grade_level": grade_level,
            "document_type": "curriculum",
            "topics": []
        }

    
 
