# Dockerfile - The optimal solution
FROM python:3.13.5-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create writable directories with proper permissions
RUN mkdir -p /.cache && chmod -R 777 /.cache
RUN mkdir -p /app/temp && chmod -R 777 /app/temp
RUN mkdir -p /app/logs && chmod -R 777 /app/logs
RUN mkdir -p /app/.streamlit && chmod -R 777 /app/.streamlit

COPY requirements.txt ./
COPY streamlit_app.py ./
COPY main.py ./
COPY components/ ./components/
COPY src/ ./src/

RUN pip3 install -r requirements.txt

EXPOSE 8501 8001

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Environment variables for file paths
ENV STREAMLIT_CONFIG_DIR=/app/.streamlit
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV TEMP_DIR=/app/temp
ENV LOG_DIR=/app/logs

# Add logging environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=DEBUG
ENV STREAMLIT_LOG_LEVEL=DEBUG


# Update permissions for all files
RUN chmod -R 777 /app


# # Create startup script
# RUN echo '#!/bin/bash\n\
# python main.py &\n\
# streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0\n\
# ' > /app/start.sh && chmod +x /app/start.sh

# Create enhanced startup script (use absolute paths, capture logs)
RUN echo '#!/bin/bash\n\
set -e\n\
echo \"[$(date)] Starting FastAPI (uvicorn)\"\n\
# Run uvicorn for the FastAPI app on port 8001 and capture logs\n\
uvicorn main:app --host 0.0.0.0 --port 8001 --log-level info > /app/logs/fastapi.log 2>&1 &\n\
sleep 1\n\
echo \"[$(date)] Starting Streamlit frontend\"\n\
export STREAMLIT_LOG_LEVEL=debug\n\
streamlit run /app/streamlit_app.py --server.port=8501 --server.address=0.0.0.0 > /app/logs/streamlit.log 2>&1\n\
' > /app/start.sh && chmod +x /app/start.sh

ENTRYPOINT ["/app/start.sh"]