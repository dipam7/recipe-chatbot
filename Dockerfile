FROM python:3.11-slim

# Install CA certificates so MongoDB TLS works
RUN apt-get update && apt-get install -y ca-certificates

# Set working dir and copy code
WORKDIR /app
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the FastAPI app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]