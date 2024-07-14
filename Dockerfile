FROM python:3.11
WORKDIR /app
COPY pyproject.toml ./
RUN pip install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --with cloud --without dev
COPY . .

EXPOSE 8080
ENV IS_DOCKER=true
ENV PYTHONPATH "${PYTHONPATH}:/app/src"
CMD ["python", "src/telegram.py"]