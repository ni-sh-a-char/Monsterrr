FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install build dependencies
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Install runtime dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose port
EXPOSE 8000

# Start command - can be overridden at runtime
# For web service: docker run -e START_MODE=web monsterrr
# For worker service: docker run -e START_MODE=worker monsterrr
CMD ["sh", "-c", "if [ \"$START_MODE\" = \"web\" ]; then python -m main web; else python -m main worker; fi"]