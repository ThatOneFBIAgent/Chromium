# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies (if any needed for aiosqlite or others, usually none for pure python sqlite)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user
RUN useradd -m botuser
USER botuser

# Copy the rest of the application
COPY . .

# Create directory for database if it doesn't exist (handled by code usually, but good for permissions)
# We might need volume mounting instructions in README

# Run the bot
CMD ["python", "bot.py"]
