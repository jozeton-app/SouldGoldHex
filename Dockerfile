FROM python:3.11-slim
WORKDIR /app
COPY . /app
EXPOSE 8080
ENV PORT=8080
ENV HOST=0.0.0.0
CMD ["python3", "soulgold_web_server.py", "--no-browser"]
