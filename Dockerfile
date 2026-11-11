FROM python:3.11-slim

WORKDIR /app

COPY servidor.py .

ENV PYTHONUNBUFFERED=1

EXPOSE 5555

CMD ["python", "servidor.py"]
