# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# --- Set Hugging Face cache directory ---
# Create a cache directory within the working directory and set HF_HOME
# This ensures the container has write permissions for downloading models/tokenizers
RUN mkdir -p /app/.cache
ENV HF_HOME=/app/.cache
# Also set TRANSFORMERS_CACHE for good measure
ENV TRANSFORMERS_CACHE=/app/.cache

# Copy the requirements file into the container at /app
# Copy only requirements first to leverage Docker layer caching
COPY backend/requirements.txt .

# Install any needed packages specified in requirements.txt
# Add --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
# Copy backend, static, and templates directories
COPY backend/ ./backend
COPY static/ ./static
COPY templates/ ./templates

# Create the uploads directory (ensure it exists)
RUN mkdir -p /app/uploads

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable (optional, can be set in HF Spaces settings too)
# ENV MODEL_NAME="Helsinki-NLP/opus-mt-en-ar"

# Run main.py when the container launches
# Use the backend subdirectory path for the module
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
