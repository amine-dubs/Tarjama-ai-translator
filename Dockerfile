# Use an official Python slim-buster runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies including Rust, build tools, pkg-config, cmake, and sentencepiece dev libs using apt-get
RUN apt-get update && apt-get install -y --no-install-recommends \
    rustc \
    cargo \
    build-essential \
    pkg-config \
    cmake \
    libsentencepiece-dev \
    # Clean up apt lists to reduce image size
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements file first to leverage Docker cache
COPY backend/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY backend/ /app/backend
COPY templates/ /app/templates
COPY static/ /app/static

# Create the necessary directories within the container that the app expects
RUN mkdir -p /app/templates /app/static /app/uploads

# Make port 8000 available
EXPOSE 8000

# Run main.py using uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
