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

# Unified startup command that can run in different modes
# For web service: docker run -e START_MODE=web monsterrr
# For worker service: docker run -e START_MODE=worker
# For hybrid (both): docker run -e START_MODE=hybrid monsterrr
# For all-in-one (worker in background, web in foreground): docker run -e START_MODE=all monsterrr
# Default (no env var): runs in all-in-one mode
CMD ["python", "start_monsterrr.py"]