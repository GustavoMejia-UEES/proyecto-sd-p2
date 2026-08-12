FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY camera_agent.py .

EXPOSE 8081

CMD ["uvicorn", "camera_agent:app", "--host", "0.0.0.0", "--port", "8081"]
