import subprocess
import time
import os
import streamlit as st
import requests
from components.content_generators import ContentGenerator
from components.ui_component import create_input_form, display_content_card, create_test_examples
from src.education_ai_system.utils.validators import extract_weeks_from_scheme


# Fix Streamlit permission issue
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
os.environ['STREAMLIT_SERVER_ENABLE_CORS'] = 'false'

# Start FastAPI in background
def start_fastapi():
    subprocess.Popen([
        "uvicorn", "main:app", 
        "--host", "0.0.0.0", 
        "--port", "8001"
    ])
    time.sleep(3)

# Start API if not running
try:
    requests.get("http://localhost:8001/", timeout=2)
except:
    start_fastapi()

# Rest of your app.py content...

# Configuration
API_BASE_URL = (
    os.getenv("API_BASE_URL")
    or "http://localhost:8001"
    )

def main():
    st.title("🎓 AI-Teacher's Content Assistant")
    st.markdown("**Nigerian Educational Content Generation System**")
    
    # Initialize session state
    if 'content' not in st.session_state:
        st.session_state.content = {}
    if 'evaluations' not in st.session_state:  # ADD THIS LINE
        st.session_state.evaluations = {}
    
    # Initialize content generator
    generator = ContentGenerator(API_BASE_URL)
    
    # Create tabs - CHANGE THIS LINE
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Upload Document", "�� Content Generation", "🔍 Evaluation & Improvement", "🧪 Test Search"])
    
    with tab1:
        upload_document_tab()
    
    with tab2:
        content_generation_tab(generator)
    
    with tab3:  # NEW TAB
        evaluation_tab()
    
    with tab4:  # RENUMBERED
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
        limitations = st.text_area("Teaching Constraints", 
                                 "Limited resources, 40 students, no projector")
    
    with col2:
        st.info(f"**Using Scheme:** `{scheme['id'][:8]}...`")
        st.info(f"**Using Lesson Plan:** `{lesson_plan['id'][:8]}...`")
    
    if st.button("📝 Generate Lesson Notes"):
        result = generator.generate_lesson_notes(scheme['id'], lesson_plan['id'],  limitations)
        
        if result:
            st.session_state.content['lesson_notes'] = {
                'id': result['lesson_notes_id'],
                'content': result['content']
            }
            st.success("✅ Lesson Notes generated successfully!")
            st.rerun()



def generate_exam_ui(generator):
    """UI for generating exam - new simplified approach"""
    scheme = st.session_state.content['scheme']
    
    #determine available weeks from the scheme
    available_weeks = extract_weeks_from_scheme(scheme['content'])
    if not available_weeks:
        available_weeks = ["1", "2", "3", "4"]

    

    col1, col2 = st.columns(2)
    
    with col1:
        selected_weeks = st.multiselect(
            "select weeks to Include",
            options = available_weeks,
            default = available_weeks[:2] if len(available_weeks) >= 2 else available_weeks
        )
    
    with col2:
        st.info(f"**Using Scheme:** `{scheme['id'][:8]}...`")
        st.info("**Note:** Exam will use ONLY lesson plans and notes for the selected weeks")
    
    if st.button("📝 Generate Exam", key="gen_exam"):
        if not selected_weeks:
            st.error("Please select at least one week")
            return
        

        try:
            weeks_int = [int(w) for w in selected_weeks]

        except Exception:
            st.error("Weeks must be number (e.g., 1, 2, 3)")
            return 
        result =  generator.generate_exam(scheme['id'], weeks_int)

        if result:
            st.session_state.content['exam'] = {
                'id': result['exam_id'],
                'content': result['content'],
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



def evaluation_tab():
    """New tab for content evaluation and improvement"""
    st.header(" Content Evaluation & Improvement")
    st.markdown("**Evaluate your generated content and get AI-powered improvements**")
    
    # Content selection
    st.subheader("📋 Select Content to Evaluate")
    
    # Get available content from session state
    available_content = []
    if 'scheme' in st.session_state.content:
        # FIX: Use context_id instead of scheme_id for scheme evaluation
        available_content.append(("scheme_of_work", "Scheme of Work", st.session_state.content['scheme']['context_id']))
    if 'lesson_plan' in st.session_state.content:
        available_content.append(("lesson_plan", "Lesson Plan", st.session_state.content['lesson_plan']['id']))
    if 'lesson_notes' in st.session_state.content:
        available_content.append(("lesson_notes", "Lesson Notes", st.session_state.content['lesson_notes']['id']))
    if 'exam' in st.session_state.content:
        available_content.append(("exam_generator", "Exam", st.session_state.content['exam']['id']))
    
    if not available_content:
        st.warning("⚠️ No content available for evaluation. Generate some content first!")
        return
    
    # Content selection dropdown
    content_options = [f"{name} ({content_id[:8]}...)" for content_type, name, content_id in available_content]
    selected_idx = st.selectbox("Choose content to evaluate:", range(len(content_options)), 
                               format_func=lambda x: content_options[x])
    
    selected_content_type, selected_name, selected_id = available_content[selected_idx]
    
    # Evaluation controls with better feedback
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button(" Evaluate Content", type="primary"):
            with st.spinner("Evaluating content..."):
                evaluate_content(selected_content_type, selected_id)
            st.rerun()  # Force refresh to show results
    
    with col2:
        if st.button("🔄 Re-evaluate"):
            eval_key = f"{selected_content_type}_{selected_id}"
            if eval_key in st.session_state.evaluations:
                del st.session_state.evaluations[eval_key]
                st.info("🔄 Previous evaluation cleared. Running new evaluation...")
            
            with st.spinner("Re-evaluating content..."):
                evaluate_content(selected_content_type, selected_id)
            st.rerun()  # Force refresh to show results
    
    with col3:
        if st.button("📊 View All Evaluations"):
            show_all_evaluations()
    
    # Display evaluation results
    eval_key = f"{selected_content_type}_{selected_id}"
    if eval_key in st.session_state.evaluations:
        display_evaluation_results(st.session_state.evaluations[eval_key], selected_name)
    else:
        st.info("💡 Click 'Evaluate Content' to see evaluation results")

def evaluate_content(content_type: str, content_id: str):
    """Evaluate content using the evaluation API"""
    try:
        # Determine the correct API endpoint based on content type
        if content_type == "scheme_of_work":
            response = requests.post(f"{API_BASE_URL}/api/evaluate/scheme", 
                                   json={"context_id": content_id})
        elif content_type == "lesson_plan":
            response = requests.post(f"{API_BASE_URL}/api/evaluate/lesson_plan", 
                                   json={"lesson_plan_id": content_id})
        elif content_type == "lesson_notes":
            response = requests.post(f"{API_BASE_URL}/api/evaluate/lesson_notes", 
                                   json={"lesson_notes_id": content_id})
        elif content_type == "exam_generator":
            response = requests.post(f"{API_BASE_URL}/api/evaluate/exam_generator", 
                                   json={"exam_id": content_id})
        else:
            st.error("❌ Unknown content type")
            return
        
        if response.status_code == 200:
            result = response.json()
            eval_key = f"{content_type}_{content_id}"
            st.session_state.evaluations[eval_key] = result
            st.success("✅ Evaluation completed successfully!")
            
            # Show a preview of the results
            overall_score = result.get('overall_accuracy', 0)
            needs_improvement = result.get('needs_improvement', False)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Overall Score", f"{overall_score}/5.0")
            with col2:
                st.metric("Needs Improvement", "Yes" if needs_improvement else "No")
                
        else:
            error_msg = response.json().get('detail', 'Unknown error')
            st.error(f"❌ Evaluation failed: {error_msg}")
            
    except Exception as e:
        st.error(f"�� Error: {str(e)}")

def display_evaluation_results(evaluation, content_name):
    """Display evaluation results with visual indicators"""
    st.subheader(f"�� Evaluation Results for {content_name}")
    
    
    # Overall accuracy score
    overall_score = evaluation.get('overall_accuracy', 0)
    composite_score = evaluation.get('composite_score', 0)  # Add this line
    bias_score = evaluation.get('bias', {}).get('score', 0)  # Add this line
    status = evaluation.get('status', 'unknown')
    
    # Color-coded overall score
    if overall_score >= 4.5:
        score_color = "��"
        score_emoji = "Excellent"
    elif overall_score >= 4.0:
        score_color = "��"
        score_emoji = "Good"
    elif overall_score >= 3.0:
        score_color = "��"
        score_emoji = "Fair"
    else:
        score_color = "��"
        score_emoji = "Needs Improvement"
    
    # Main metrics in a more prominent layout
    st.markdown("---")
    
    # Overall score in a large, prominent box
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])  # Add col4

    with col1:
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center; margin: 10px 0;">
            <h2 style="margin: 0; color: #1f2937;">Overall Accuracy</h2>
            <h1 style="margin: 10px 0; color: #059669; font-size: 3em;">{overall_score}/5.0</h1>
            <p style="margin: 0; font-size: 1.2em; color: #6b7280;">{score_color} {score_emoji}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background-color: #e0f2fe; padding: 15px; border-radius: 10px; text-align: center; margin: 10px 0;">
            <h3 style="margin: 0; color: #0369a1;">Bias Score</h3>
            <h2 style="margin: 5px 0; color: #0369a1; font-size: 2em;">{bias_score}/5.0</h2>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="background-color: #f0fdf4; padding: 15px; border-radius: 10px; text-align: center; margin: 10px 0;">
            <h3 style="margin: 0; color: #166534;">Composite Score</h3>
            <h2 style="margin: 5px 0; color: #166534; font-size: 2em;">{composite_score}/5.0</h2>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        needs_improvement = evaluation.get('needs_improvement', False)
        improvement_text = "✅ Needed" if needs_improvement else "❌ Not Needed"
        improvement_color = "#dc2626" if needs_improvement else "#059669"
        
        st.markdown(f"""
        <div style="background-color: #f3f4f6; padding: 15px; border-radius: 10px; text-align: center; margin: 10px 0;">
            <h3 style="margin: 0; color: {improvement_color};">Improvement</h3>
            <p style="margin: 5px 0; font-size: 1.1em; color: {improvement_color};">{improvement_text}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Detailed metrics with better layout
    st.subheader("📈 Detailed Metrics")
    
    # Accuracy metrics
    accuracy = evaluation.get('accuracy', {})
    bias = evaluation.get('bias', {})
    
    # Create a 2x3 grid for better readability
    col1, col2, col3 = st.columns(3)
    
    metrics = [
        ("curriculum_compliance", "Curriculum Compliance", accuracy.get('curriculum_compliance', {})),
        ("topic_relevance", "Topic Relevance", accuracy.get('topic_relevance', {})),
        ("content_consistency", "Content Consistency", accuracy.get('content_consistency', {})),
        ("quality_readability", "Quality & Readability", accuracy.get('quality_readability', {})),
        ("cultural_relevance", "Cultural Relevance", accuracy.get('cultural_relevance', {})),
        ("bias", "Bias Assessment", bias)
    ]
    
    # Display metrics in a 2x3 grid
    for i, (key, label, metric) in enumerate(metrics):
        with [col1, col2, col3][i % 3]:
            score = metric.get('score', 0)
            reason = metric.get('reason', 'No reason provided')
            
            # Color coding
            if score >= 4.5:
                color = "#059669"  # Green
                bg_color = "#d1fae5"
                emoji = "🟢"
            elif score >= 4.0:
                color = "#d97706"  # Yellow
                bg_color = "#fef3c7"
                emoji = "🟡"
            elif score >= 3.0:
                color = "#ea580c"  # Orange
                bg_color = "#fed7aa"
                emoji = "🟠"
            else:
                color = "#dc2626"  # Red
                bg_color = "#fecaca"
                emoji = "🔴"
            
            # Create metric card
            st.markdown(f"""
            <div style="background-color: {bg_color}; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 4px solid {color};">
                <h4 style="margin: 0 0 10px 0; color: {color}; font-size: 1.1em;">{emoji} {label}</h4>
                <h2 style="margin: 0 0 10px 0; color: {color}; font-size: 2em;">{score}/5</h2>
                <details style="margin-top: 10px;">
                    <summary style="cursor: pointer; color: {color}; font-weight: bold;">📝 View Reason</summary>
                    <p style="margin: 10px 0 0 0; padding: 10px; background-color: white; border-radius: 5px; font-size: 0.95em; line-height: 1.4;">{reason}</p>
                </details>
            </div>
            """, unsafe_allow_html=True)
    
    # Improvement section with better styling
    if needs_improvement:
        st.markdown("---")
        st.subheader("🔧 AI-Powered Improvements")
        
        improved_content = evaluation.get('improved_content')
        change_log = evaluation.get('change_log', [])
        improved_evaluation = evaluation.get('improved_evaluation')
        
        if improved_content:
            st.success("✅ **Improved content generated!**")
            
            # Show change log in a better format
            if change_log:
                st.markdown("#### 📝 Changes Made:")
                for i, change in enumerate(change_log, 1):
                    st.markdown(f"**{i}.** {change}")
            
            # Show improved content in a better container
            with st.expander("📄 View Improved Content", expanded=True):
                st.markdown("""
                <div style="background-color: #f8fafc; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0;">
                """, unsafe_allow_html=True)
                st.markdown(improved_content)
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Show improved evaluation if available
            if improved_evaluation:
                st.markdown("#### 📊 Improved Evaluation")
                improved_overall = improved_evaluation.get('overall_accuracy', 0)
                improvement = improved_overall - overall_score
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("New Overall Score", f"{improved_overall}/5.0")
                with col2:
                    st.metric("Improvement", f"+{improvement:.1f}", delta=f"{improvement:.1f}")
                
                # Download improved content
                if st.button("💾 Download Improved Content", type="primary"):
                    download_improved_content(improved_content, content_name)
        else:
            st.warning("⚠️ No improvements were generated. The content may already be at an acceptable quality level.")
    
    # Low metrics section
    low_metrics = evaluation.get('low_metrics', [])
    if low_metrics:
        st.markdown("---")
        st.subheader("⚠️ Areas for Improvement")
        for metric in low_metrics:
            st.markdown(f"• **{metric.replace('_', ' ').title()}**")

def download_improved_content(content: str, content_name: str):
    """Download improved content as text file"""
    filename = f"improved_{content_name.lower().replace(' ', '_')}.txt"
    st.download_button(
        label="💾 Download Improved Content",
        data=content,
        file_name=filename,
        mime="text/plain"
    )

def show_all_evaluations():
    """Show all evaluations in a summary view"""
    st.subheader("📊 All Evaluations Summary")
    
    if not st.session_state.evaluations:
        st.info("No evaluations available. Evaluate some content first!")
        return
    
    for eval_key, evaluation in st.session_state.evaluations.items():
        content_type, content_id = eval_key.split('_', 1)
        overall_score = evaluation.get('overall_accuracy', 0)
        needs_improvement = evaluation.get('needs_improvement', False)
        
        with st.expander(f"{content_type.title()} - Score: {overall_score}/5.0", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Content ID:** {content_id}")
                st.write(f"**Status:** {'Needs Improvement' if needs_improvement else 'Good'}")
            with col2:
                if st.button(f"View Details", key=f"view_{eval_key}"):
                    display_evaluation_results(evaluation, content_type.title())

if __name__ == "__main__":
    main()
