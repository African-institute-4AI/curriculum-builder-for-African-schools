import streamlit as st
from typing import List, Optional

def create_input_form(prefix: str = "") -> tuple:
    """Create flexible input form without hardcoded validation"""
    st.subheader("Content Parameters")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        subject = st.text_input("Subject", placeholder="e.g., mathematics, english", key=f"{prefix}_subject")
    
    with col2:
        grade_level = st.text_input("Grade Level", placeholder="e.g., primary four, sss 1", key=f"{prefix}_grade")
    
    with col3:
        topic = st.text_input("Topic", placeholder="e.g., fractions, algebra", key=f"{prefix}_topic")
    
    # Test mode toggle
    test_mode = st.checkbox("🧪 Test Mode (Check similarity search)", key=f"{prefix}_test_mode")
    
    if test_mode:
        st.info("Test Mode: This will show what content exists in the database for similar queries")
    
    return subject, grade_level, topic, test_mode

def display_content_card(title: str, content_id: str, content: str):
    """Reusable content display card - NO EVALUATION"""
    with st.container(border=True):
        st.markdown(f"### {title}")
        st.markdown(f"**ID:** `{content_id}`")
        
        # Content preview
        with st.expander("View Content", expanded=False):
            st.markdown(content)

def create_test_examples():
    """Show test examples for similarity search"""
    with st.expander("📋 Test Examples", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**✅ Should Work (Based on your data):**")
            st.code("mathematics, primary four, fractions")
            st.code("mathematics, primary four, division")
            st.code("mathematics, primary four, multiplication")
        
        with col2:
            st.markdown("**❌ Should Fail (Test cases):**")
            st.code("mathematics, primary three, fractions")
            st.code("english, primary four, grammar")
            st.code("physics, sss 1, mechanics")