# Demo server. Mount the Swarm Traces dump and your results, and pass the key:
#   docker run -p 8000:8000 -e TYPESAFE_API_KEY=... -v ~/Downloads/redacted.jsonl.gz:/data/redacted.jsonl.gz \
#     -v $PWD/results:/app/results jev-sentinel
FROM python:3.12-slim
WORKDIR /app
COPY . .
ENV SENTINEL_HOST=0.0.0.0 SWARM_TRACES=/data/redacted.jsonl.gz
EXPOSE 8000
CMD ["python3", "server.py"]
