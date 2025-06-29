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

# Copy frontend application code
COPY ./frontend /app/frontend

# Expose port (Streamlit default is 8501)
EXPOSE 8501

# Command to run the application
# Assuming app.py is in /app/frontend/
CMD ["streamlit", "run", "frontend/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
