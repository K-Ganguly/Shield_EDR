# Dockerfile for EDR Agent
FROM python:3.9-slim

WORKDIR /agent
COPY . /agent

RUN pip install -r requirements.txt

CMD ["python", "agent.py"]
