import streamlit as st
import requests
from components.content_generators import ContentGenerator
from components.ui_component import create_input_form, display_content_card, create_test_examples
from src.education_ai_system.utils.validators import extract_weeks_from_scheme

# Configuration
API_BASE_URL = "http://localhost:8001"

def main():
    st.title("🎓 AI-Teacher's Content Assistant")
    st.markdown("**Nigerian Educational Content Generation System**")
    
    # Initialize session state
    if 'content' not in st.session_state:
        st.session_state.content = {}
    
    # Initialize content generator
    generator = ContentGenerator(API_BASE_URL)
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📄 Upload Document", "📚 Content Generation", "🧪 Test Search"])
    
    with tab1:
        upload_document_tab()
    
    with tab2:
        content_generation_tab(generator)
    
    with tab3:
        test_search_tab()

def upload_document_tab():
    """Simple PDF upload and processing tab"""
    st.header("📄 Upload Curriculum Document")
    st.markdown("**Upload your curriculum PDF to store in Pinecone for content generation**")

    # Add country selection for upload
    country = st.selectbox(
        "Select Country",
        ["nigeria", "ghana", "kenya", "south_africa"],
        index=0,
        key="upload_country"
    )
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose a PDF file", 
        type=['pdf'],
        help="Upload the curriculum document you want to use for content generation"
    )
    
    if uploaded_file:
        st.success(f"✅ **File Selected:** {uploaded_file.name}")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if st.button("🚀 Process & Store in Pinecone", type="primary"):
                process_pdf_file(uploaded_file, country)  # Now country is defined
        
        with col2:
            if st.button("🗑️ Clear Database"):
                clear_pinecone_index()
    
    st.divider()
    
    # Database status
    st.subheader("📊 Database Status")
    if st.button("🔍 Check What's Stored"):
        check_database_contents()

def process_pdf_file(uploaded_file, country):  # Add country parameter
    """Process single PDF file and store in Pinecone"""
    try:
        # Prepare file for API
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
        data = {"country": country}  # Add country data
        
        with st.spinner(f"Processing {uploaded_file.name} and storing in Pinecone..."):
            response = requests.post(f"{API_BASE_URL}/api/embeddings/process_pdf", files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            st.success("✅ **PDF processed successfully!**")
            st.info("📝 Your document is now ready for content generation")
            
            # Show result details
            with st.expander("📋 Processing Details"):
                st.json(result)
        else:
            error_msg = response.json().get('detail', 'Unknown error')
            st.error(f"❌ **Processing failed:** {error_msg}")
            
    except Exception as e:
        st.error(f"🚨 **Error:** {str(e)}")

def clear_pinecone_index():
    """Clear Pinecone database"""
    try:
        with st.spinner("Clearing Pinecone database..."):
            response = requests.post(f"{API_BASE_URL}/api/embeddings/clear-index-test")
        
        if response.status_code == 200:
            st.success("✅ **Database cleared successfully!**")
            st.info("📝 You can now upload a new document")
        else:
            st.error("❌ **Failed to clear database**")
            
    except Exception as e:
        st.error(f"🚨 **Error:** {str(e)}")
def check_database_contents():
    """Check what's stored in the database"""
    try:
        with st.spinner("🔍 Checking database contents..."):
            response = requests.get(f"{API_BASE_URL}/api/embeddings/debug-index")
        
        if response.status_code == 200:
            result = response.json()
            st.success("✅ **Database Status Check Complete**")
            
            # Display database statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Vectors", result.get('total_vectors', 0))
            with col2:
                st.metric("Subjects Found", len(result.get('subjects_found', [])))
            with col3:
                st.metric("Grade Levels", len(result.get('grade_levels_found', [])))
            
            # Show what's actually stored
            if result.get('subjects_found'):
                st.subheader("📚 Subjects in Database:")
                for subject in result.get('subjects_found', []):
                    st.write(f"• {subject}")
            
            if result.get('grade_levels_found'):
                st.subheader("📊 Grade Levels in Database:")
                for grade in result.get('grade_levels_found', []):
                    st.write(f"• {grade}")
            
            # Show sample content
            if result.get('sample_matches'):
                with st.expander("📝 Sample Content Preview"):
                    for i, match in enumerate(result.get('sample_matches', [])[:3]):
                        st.write(f"**Match {i+1}:**")
                        st.write(f"Subject: {match.get('subject', 'Unknown')}")
                        st.write(f"Grade: {match.get('grade_level', 'Unknown')}")
                        st.write(f"Content: {match.get('content_preview', '')[:100]}...")
                        st.divider()
        else:
            st.error(f"❌ **Database check failed:** {response.json().get('detail', 'Unknown error')}")
            
    except Exception as e:
        st.error(f"�� **Connection Error:** {str(e)}")
        st.info("�� Make sure your API server is running on port 8001")

def content_generation_tab(generator):
    """Complete 4-step content generation workflow"""
    st.header("Content Generation Workflow")
    
    # Step 1: Scheme of Work
    with st.expander("1. Generate Scheme of Work", expanded=True):
        if 'scheme' in st.session_state.content:
            scheme = st.session_state.content['scheme']
            st.success(f"✅ **Scheme Generated:** `{scheme['id']}`")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                with st.expander("View Scheme Content"):
                    st.markdown(scheme['content'])
            with col2:
                if st.button("� Download DOCX", key="download_scheme"):
                    download_document("scheme", scheme['id'])
            
            if st.button("�🔄 Generate New Scheme", key="new_scheme"):
                st.session_state.content = {}
                st.rerun()
        else:
            generate_scheme_ui(generator)
    
    # Step 2: Lesson Plan
    with st.expander("2. Generate Lesson Plan", expanded='scheme' in st.session_state.content):
        if 'lesson_plan' in st.session_state.content:
            lesson_plan = st.session_state.content['lesson_plan']
            st.success(f"✅ **Lesson Plan Generated:** `{lesson_plan['id']}`")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                with st.expander("View Lesson Plan Content"):
                    st.markdown(lesson_plan['content'])
            with col2:
                if st.button("📄 Download DOCX", key="download_lesson_plan"):
                    download_document("lesson_plan", lesson_plan['id'])
                
            if st.button("🔄 Generate New Lesson Plan", key="new_lesson_plan"):
                if 'lesson_plan' in st.session_state.content:
                    del st.session_state.content['lesson_plan']
                if 'lesson_notes' in st.session_state.content:
                    del st.session_state.content['lesson_notes']
                if 'exam' in st.session_state.content:
                    del st.session_state.content['exam']
                st.rerun()
        elif 'scheme' in st.session_state.content:
            generate_lesson_plan_ui(generator)
        else:
            st.warning("Generate a Scheme of Work first")
    
    # Step 3: Lesson Notes
    with st.expander("3. Generate Lesson Notes", expanded='lesson_plan' in st.session_state.content):
        if 'lesson_notes' in st.session_state.content:
            lesson_notes = st.session_state.content['lesson_notes']
            st.success(f"✅ **Lesson Notes Generated:** `{lesson_notes['id']}`")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                with st.expander("View Lesson Notes Content"):
                    st.markdown(lesson_notes['content'])
            with col2:
                if st.button("📄 Download DOCX", key="download_lesson_notes"):
                    download_document("lesson_notes", lesson_notes['id'])
                
            if st.button("🔄 Generate New Lesson Notes", key="new_lesson_notes"):
                if 'lesson_notes' in st.session_state.content:
                    del st.session_state.content['lesson_notes']
                if 'exam' in st.session_state.content:
                    del st.session_state.content['exam']
                st.rerun()
        elif 'lesson_plan' in st.session_state.content:
            generate_lesson_notes_ui(generator)
        else:
            st.warning("Generate a Lesson Plan first")
    
    # Step 4: Exam Generation
    with st.expander("4. Generate Exam", expanded='lesson_notes' in st.session_state.content):
        if 'exam' in st.session_state.content:
            exam = st.session_state.content['exam']
            st.success(f"✅ **Exam Generated:** `{exam['id']}`")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                with st.expander("View Exam Content"):
                    st.markdown(exam['content'])
            with col2:
                if st.button("📄 Download DOCX", key="download_exam"):
                    download_document("exam_generator", exam['id'])
                
            if st.button("🔄 Generate New Exam", key="new_exam"):
                if 'exam' in st.session_state.content:
                    del st.session_state.content['exam']
                st.rerun()
        elif 'lesson_notes' in st.session_state.content:
            generate_exam_ui(generator)
        else:
            st.warning("Generate Lesson Notes first")
def download_document(content_type: str, content_id: str, custom_filename: str = None):
    """Download document as DOCX"""
    try:
        payload = {
            "content_type": content_type,
            "custom_filename": custom_filename
        }
        
        # Add the appropriate ID field
        if content_type == "scheme":
            payload["scheme_of_work_id"] = content_id
        elif content_type == "lesson_plan":
            payload["lesson_plan_id"] = content_id
        elif content_type == "lesson_notes":
            payload["lesson_notes_id"] = content_id
        elif content_type == "exam_generator":
            payload["exam_id"] = content_id
        
        with st.spinner("Generating document..."):
            response = requests.post(f"{API_BASE_URL}/api/convert/generate-document", json=payload)
        
        if response.status_code == 200:
            # Get filename from headers
            content_disposition = response.headers.get('content-disposition', '')
            filename = "document.docx"
            if 'filename=' in content_disposition:
                filename = content_disposition.split('filename=')[1].strip('"')
            
            # Create download button
            st.download_button(
                label="💾 Download DOCX",
                data=response.content,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            st.success("✅ Document ready for download!")
        else:
            st.error(f"❌ Download failed: {response.json().get('detail', 'Unknown error')}")
            
    except Exception as e:
        st.error(f"🚨 Download error: {str(e)}")
def generate_scheme_ui(generator):
    """UI for generating scheme of work"""
    subject, grade_level, topic, test_mode = create_input_form("scheme")
    
    # Add country selection here
    country = st.selectbox(
        "Select Country",
        ["nigeria", "ghana", "kenya", "south_africa"],
        index=0,
        key="scheme_country"
    )
    
    if st.button("🚀 Generate Scheme of Work", type="primary"):
        if not all([subject, grade_level, topic]):
            st.error("Please fill in all fields")
            return
        
        if test_mode:
            st.info(f"🔍 **Testing Search:** {subject} | {grade_level} | {topic}")
        
        result = generator.generate_scheme(subject, grade_level, topic, country)  # Pass country
        
        if result:
            st.session_state.content['scheme'] = {
                'id': result['scheme_of_work_id'],
                'content': result['scheme_of_work_output'],
                'context_id': result['context_id']
            }
            st.success("✅ Scheme of Work generated successfully!")
            st.rerun()

def generate_lesson_plan_ui(generator):
    """UI for generating lesson plan"""
    scheme = st.session_state.content['scheme']
    
    # Extract weeks from scheme
    weeks = extract_weeks_from_scheme(scheme['content'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_week = st.selectbox("Select Week", weeks if weeks else ["1", "2", "3", "4"])
        limitations = st.text_area("Teaching Constraints", 
                                 "Limited resources, 40 students, no projector")
    
    with col2:
        st.info(f"**Using Scheme:** `{scheme['id'][:8]}...`")
    
    if st.button("📝 Generate Lesson Plan"):
        result = generator.generate_lesson_plan(scheme['id'], int(selected_week), limitations)
        
        if result:
            st.session_state.content['lesson_plan'] = {
                'id': result['lesson_plan_id'],
                'content': result['lesson_plan_output']
            }
            st.success("✅ Lesson Plan generated successfully!")
            st.rerun()

def generate_lesson_notes_ui(generator):
    """UI for generating lesson notes"""
    scheme = st.session_state.content['scheme']
    lesson_plan = st.session_state.content['lesson_plan']
    
    col1, col2 = st.columns(2)
    
    with col1:
        week = lesson_plan.get('week', '1')
        st.info(f"**Week:** {week}")
        limitations = st.text_area("Teaching Constraints", 
                                 "Limited resources, 40 students, no projector")
    
    with col2:
        st.info(f"**Using Scheme:** `{scheme['id'][:8]}...`")
        st.info(f"**Using Lesson Plan:** `{lesson_plan['id'][:8]}...`")
    
    if st.button("📝 Generate Lesson Notes"):
        result = generator.generate_lesson_notes(scheme['id'], lesson_plan['id'], int(week), limitations)
        
        if result:
            st.session_state.content['lesson_notes'] = {
                'id': result['lesson_notes_id'],
                'content': result['content']
            }
            st.success("✅ Lesson Notes generated successfully!")
            st.rerun()

# def generate_exam_ui(generator):
#     """UI for generating exam - minimal constraints"""
#     scheme = st.session_state.content['scheme']
#     lesson_plan = st.session_state.content['lesson_plan']
#     lesson_notes = st.session_state.content['lesson_notes']
    
#     col1, col2 = st.columns(2)
    
#     with col1:
#         exam_duration = st.selectbox("Exam Duration", ["1 hour", "2 hours", "3 hours"], index=1, key="exam_duration")
#         total_marks = st.number_input("Total Marks", min_value=50, max_value=200, value=100, key="exam_marks")
#         week = lesson_plan.get('week', '1')
#         st.info(f"**Week:** {week}")
    
#     with col2:
#         st.info(f"**Using Scheme:** `{scheme['id'][:8]}...`")
#         st.info(f"**Using Lesson Plan:** `{lesson_plan['id'][:8]}...`")
#         st.info(f"**Using Lesson Notes:** `{lesson_notes['id'][:8]}...`")
    
#     if st.button("📝 Generate Exam", key="gen_exam"):
#         result = generator.generate_exam(
#             scheme['id'], 
#             lesson_plan['id'], 
#             lesson_notes['id'],
#             int(week),
#             exam_duration,
#             total_marks
#         )
        
#         if result:
#             st.session_state.content['exam'] = {
#                 'id': result['exam_id'],
#                 'content': result['content'],
#                 'week': week
#             }
#             st.success("✅ Exam generated successfully!")
#             st.rerun()

def generate_exam_ui(generator):
    """UI for generating exam - new simplified approach"""
    scheme = st.session_state.content['scheme']
    
    col1, col2 = st.columns(2)
    
    with col1:
        exam_type = st.selectbox(
            "Exam Type", 
            ["quiz", "mid_term", "end_of_term", "final_exam"], 
            index=0,
            help="Quiz: weeks 1-2, Mid-term: weeks 1-7, End-term: weeks 1-13, Final: weeks 1-37"
        )
    
    with col2:
        st.info(f"**Using Scheme:** `{scheme['id'][:8]}...`")
        st.info("**Note:** Exam will use ALL available lesson plans and notes")
    
    if st.button("📝 Generate Exam", key="gen_exam"):
        result = generator.generate_exam(scheme['id'], exam_type)
        
        if result:
            st.session_state.content['exam'] = {
                'id': result['exam_id'],
                'content': result['content'],
                'exam_type': exam_type,
                'weeks_covered': result.get('weeks_covered', [])
            }
            st.success("✅ Exam generated successfully!")
            st.rerun()

def test_search_tab():
    """Tab for testing search functionality"""
    st.header("🧪 Test Search & Similarity")
    st.markdown("**Test what content exists in your database for different queries**")
    
    create_test_examples()
    st.divider()
    
    # Test form - ADD PREFIX HERE
    subject, grade_level, topic, _ = create_input_form("test")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("🔍 Test Search", type="primary", key="test_search"):
            if not all([subject, grade_level, topic]):
                st.error("Please fill in all fields")
                return
            
            test_search_functionality(subject, grade_level, topic)
    
    with col2:
        if st.button("🎯 Quick Test: Primary 3", key="quick_test"):
            test_search_functionality("mathematics", "primary three", "fractions")

def test_search_functionality(subject: str, grade_level: str, topic: str):
    """Test the search functionality"""
    st.markdown("---")
    st.markdown(f"### 🔍 Testing: `{subject}` | `{grade_level}` | `{topic}`")
    
    payload = {"subject": subject, "grade_level": grade_level, "topic": topic}
    
    try:
        with st.spinner("Testing search..."):
            response = requests.post(f"{API_BASE_URL}/api/content/scheme-of-work", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            st.success("✅ **MATCH FOUND** - Content exists in database!")
            
            # Show some details
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Content Length", f"{len(result.get('scheme_of_work_output', ''))} chars")
            with col2:
                st.metric("Scheme ID", f"{result.get('scheme_of_work_id', 'N/A')[:8]}...")
            
            # Show preview
            with st.expander("Preview Generated Content"):
                content = result.get('scheme_of_work_output', '')
                st.markdown(content[:500] + "..." if len(content) > 500 else content)
                
        else:
            error_detail = response.json().get('detail', 'Unknown error')
            st.error(f"❌ **NO MATCH** - {error_detail}")
            
            # Show what was attempted
            st.json({
                "attempted_query": payload,
                "status_code": response.status_code,
                "error": error_detail
            })
            
    except Exception as e:
        st.error(f"🚨 **CONNECTION ERROR:** {str(e)}")

if __name__ == "__main__":
    main()
