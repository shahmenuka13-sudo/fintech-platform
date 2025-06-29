# Base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt requirements.txt

# Install dependencies
# We will install all dependencies here for now, but for a more optimized build
# you might have separate requirements for backend and frontend, or use multi-stage builds.
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY ./backend /app/backend

# Expose port (FastAPI default is 8000)
EXPOSE 8000

# Command to run the application
# Adjust the entrypoint based on your main FastAPI file location
# Assuming main.py is in /app/backend/
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
