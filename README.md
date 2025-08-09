# Curriculum Builder AI System

This project is an AI-powered curriculum builder designed to assist educators in generating schemes of work, lesson plans, and lesson notes based on Nigerian academic standards. The system leverages machine learning and natural language processing tools, such as Pinecone for vector similarity search and Exa API for contextual web searches, to retrieve relevant educational materials and metadata, improving the content generation process. This tool is especially useful for creating structured and culturally relevant lesson materials tailored to specific subjects, grade levels, and topics.

---

## Table of Contents
- [Features](#features)
- [Project Structure](#project-structure)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Setup](#setup)
    - [Windows and Mac OS](#windows-and-mac-os)
- [Usage](#usage)
  - [Run the Main Script](#run-the-main-script)
  - [Converting Logs to Word Documents](#converting-logs-to-word-documents)
- [Troubleshooting](#troubleshooting)
- [Environment Variables](#environment-variables)

---

## Features

- **Automated Curriculum Generation:** Automatically generates schemes of work, lesson plans, and lesson notes based on user inputs.
- **Pinecone Integration:** Retrieves relevant context and metadata from a Pinecone vector database.
- **Exa API Integration:** Contextually fetches relevant information from the web to enrich lesson content.
- **Export to Word:** Converts generated `.md` log files into Word documents for easy download and access.

---

## Project Structure
```bash
├── src
│   └── education_ai_system
│       ├── crew.py                   # Defines the crew and tasks for the curriculum generation agents
│       ├── main.py                   # Main script to run the curriculum generation process
│       ├── config                    # YAML configuration files for agents and tasks
│       │   ├── agents.yaml           # Agent definitions (roles, goals, backstories)
│       │   └── tasks.yaml            # Task definitions (descriptions, expected outputs)
│       ├── tools                     # Custom tool integrations (Pinecone, Exa)
│       │   └── pinecone_exa_tools.py # Pinecone and Exa tool classes for data retrieval
│       ├── data_processing           # Data processing and chunking utilities
│       │   ├── pdf_extractor.py      # PDF text and table extraction
│       │   └── text_chunker.py       # Text chunking functionality
│       └── utils                     # Utility functions (e.g., document conversion)
├── logs                              # Contains generated markdown logs
├── genai_output                      # Contains converted Word documents from logs
└── README.md                         # Project documentation

```

## Installation
### Prerequisites
- Python 3.10 or lower
- Poetry (for dependency management)
- Access to Pinecone and Exa API accounts

### Setup
**Windows and Mac OS**
1. **Clone the Repository:**
```bash
git clone https://github.com/yourusername/curriculum_builder.git
cd curriculum_builder
```
2. **Install Python Dependencies:**
Ensure Poetry is installed. If not, you can install it with:
```bash
pip install poetry
```
3. **Set Up Environment Variables:**
Create a .env file in the root directory with the following variables:
```bash
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=your_pinecone_index_name
EXASEARCH_API_KEY=your_exa_api_key
OPENAI_API_KEY=your_openai_api_key
```
4. **Install Dependencies:**
Use Poetry to install project dependencies:
```bash
poetry install
```
5. **Activate Virtual Environment:**
```bash
poetry shell
```
---
## Usage
### Run the Main Script
The main script main.py initiates the curriculum generation process by executing the configured agents and tasks.
```bash
python src/education_ai_system/main.py
```
### Converting Logs to Word Documents
Use convert_logs_to_docx.py to convert .md logs into .docx files.
```bash
python src/education_ai_system/convert_logs_to_docx.py
```
---

## Troubleshooting
- **Pinecone Initialization Issues:** Ensure the Pinecone index name is correct and accessible.
- **Tokenizers Parallelism Warning:** Set TOKENIZERS_PARALLELISM=false in your environment variables.
---

## Environment Variables
Add the following keys to the .env file:
```bash
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=your_pinecone_index_name
EXASEARCH_API_KEY=your_exa_api_key
OPENAI_API_KEY=your_openai_api_key
```

