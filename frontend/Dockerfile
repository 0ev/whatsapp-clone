FROM python:3.12

WORKDIR /

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY ./app .

CMD ["python", "/app.py"]
