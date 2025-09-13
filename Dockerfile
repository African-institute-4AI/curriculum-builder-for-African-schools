FROM python:3.13.5-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Add this line to your Dockerfile after WORKDIR /app
RUN mkdir -p /.cache && chmod -R 777 /.cache

COPY requirements.txt ./
COPY streamlit_app.py ./
COPY main.py ./
COPY components/ ./components/
COPY src/ ./src/

RUN pip3 install -r requirements.txt

EXPOSE 8501 8001

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENV STREAMLIT_CONFIG_DIR=/app/.streamlit
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

RUN mkdir -p /app/.streamlit

# Create startup script that runs both services
RUN echo '#!/bin/bash\n\
python main.py &\n\
streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0\n\
' > /app/start.sh && chmod +x /app/start.sh

ENTRYPOINT ["/app/start.sh"]