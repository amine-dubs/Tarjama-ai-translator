# Use an official Python Alpine runtime as a parent image for smaller size
FROM python:3.13-alpine

# Set the working directory in the container
# All subsequent commands (COPY, RUN, CMD) use this path
WORKDIR /app

# Install system dependencies including Rust, build tools, pkgconfig, and cmake
RUN apk add --no-cache cargo build-base pkgconfig cmake
# Example for PyMuPDF (uncomment if needed, might require different packages on Alpine 3.13+):
# RUN apk add --no-cache mujs-dev freetype-dev harfbuzz-dev jpeg-dev openjpeg-dev zlib-dev tiff-dev lcms2-dev

# Copy only the requirements file first to leverage Docker cache
COPY backend/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
# This includes the backend directory, templates, static files etc.
# Adjust the source paths based on your project structure relative to the Dockerfile location
COPY backend/ /app/backend
COPY templates/ /app/templates
COPY static/ /app/static
# We don't copy uploads dir, it will be created by the app if needed

# Create the necessary directories within the container that the app expects
# Although the app tries to create them, it's good practice for Dockerfile to ensure they exist
RUN mkdir -p /app/templates /app/static /app/uploads

# Make port 8000 available to the world outside this container
# Hugging Face Spaces often map to this port from the outside world (port 7860 is also common)
EXPOSE 8000

# Define environment variable (optional)
# ENV NAME World

# Run main.py using uvicorn when the container launches
# The command needs to specify the location of the app module (backend.main:app)
# Host 0.0.0.0 makes it accessible from outside the container
# Add --reload flag for development if needed, but remove for production
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
