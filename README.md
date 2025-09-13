---
title: AI Curriculum Builder for Africa
emoji: 🎓
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
license: mit
app_port: 8501
---

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