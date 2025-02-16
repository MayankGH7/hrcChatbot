FROM python:3.12

WORKDIR /app

EXPOSE 8501

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY . .

CMD ["streamlit", "run", "app.py"]
