import os
import time
import subprocess
import requests

PORT = os.getenv("PORT", "8501")  # Railway assigns this for the web service
API_PORT = os.getenv("API_PORT", "8001")

def wait_for_api(url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False

def main():
    # 1) Start FastAPI (backend) in the background
    uvicorn_proc = subprocess.Popen([
        "uvicorn", "main:app",
        "--host", "0.0.0.0",
        "--port", API_PORT
    ])

    # 2) Point Streamlit to the local API
    os.environ["API_BASE_URL"] = f"http://localhost:{API_PORT}"

    # 3) Wait for API to become responsive (best effort)
    wait_for_api(f"http://localhost:{API_PORT}/")

    # 4) Start Streamlit (frontend) in the foreground on Railway's PORT
    try:
        subprocess.check_call([
            "streamlit", "run", "streamlit_app.py",
            "--server.port", str(PORT),
            "--server.address", "0.0.0.0"
        ])
    finally:
        # If Streamlit exits, stop uvicorn
        uvicorn_proc.terminate()
        try:
            uvicorn_proc.wait(timeout=5)
        except Exception:
            uvicorn_proc.kill()

if __name__ == "__main__":
    main()