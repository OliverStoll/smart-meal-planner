FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY src/ /app/src
COPY . .

EXPOSE 8080
ENV IS_DOCKER=true
ENV PYTHONPATH "${PYTHONPATH}:/app/src"
CMD ["python", "src/telegram.py"]