---
title: AI Curriculum Builder for Africa
emoji: 🦀
colorFrom: blue
colorTo: green
sdk: streamlit
pinned: false
license: mit
app_port: 8501
short_description: AI curriculum builder app
---

# Curriculum Builder AI System

This project is an AI-powered curriculum builder designed to assist educators in generating schemes of work, lesson plans, and lesson notes based on Nigerian academic standards. The system leverages machine learning and natural language processing tools, such as Pinecone for vector similarity search and Exa API for contextual web searches, to retrieve relevant educational materials and metadata, improving the content generation process. This tool is especially useful for creating structured and culturally relevant lesson materials tailored to specific subjects, grade levels, and topics.


# AI Curriculum Builder for Africa

This is a Streamlit application for building AI curriculum tailored for African schools.

## Features

- Interactive curriculum builder
- AI-powered recommendations
- Customizable for different educational levels
- Built with Streamlit and deployed via Docker

## Usage

Visit the live application at: https://huggingface.co/spaces/aljebra/AI_curriculum_builder_for_Africa

## Development

To run locally:

```bash
pip install -r requirements.txt
streamlit run src/streamlit_app.py
```

## Docker


```bash
docker build -t curriculum-builder .
docker run -p 8501:8501 curriculum-builder
```

# Welcome to Streamlit!

Edit `/src/streamlit_app.py` to customize this app to your heart's desire. :heart:

If you have any questions, checkout our [documentation](https://docs.streamlit.io) and [community
forums](https://discuss.streamlit.io).