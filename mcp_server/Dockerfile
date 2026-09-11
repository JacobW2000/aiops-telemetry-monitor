FROM python:3.11-slim

WORKDIR /app

# Copy dependency files if they exist and install them
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Copy server code
COPY . .

EXPOSE 8001

CMD ["python", "server.py"]