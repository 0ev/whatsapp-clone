FROM python:3.11

WORKDIR /

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the app directory
COPY ./app /app

# Copy the Python wait-for-service script
COPY wait-for-it.py /wait-for-it.py

# Start the application using the Python script to wait for PostgreSQL
CMD ["python", "/wait-for-it.py", "postgres", "5432", "sh", "-c", "python -m app.scripts.create_tables && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app"]
