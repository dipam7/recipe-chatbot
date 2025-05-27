FROM debian:bullseye

RUN apt-get update && apt-get install -y python3 python3-pip ca-certificates

WORKDIR /app
COPY . /app
RUN pip3 install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]