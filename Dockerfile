FROM nitedani/playwright-python:latest

# Set working directory
WORKDIR /app

# Copy your application code
COPY . .

# Command to run your application
CMD ["python", "api.py"]