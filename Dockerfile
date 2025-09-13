FROM python:3.13.5-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
COPY streamlit_app.py ./
COPY src/ ./src/
COPY components/ ./components/

RUN pip3 install -r requirements.txt

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENV STREAMLIT_CONFIG_DIR=/app/.streamlit
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

RUN mkdir -p /app/.streamlit

ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]