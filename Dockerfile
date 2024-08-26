FROM nitedani/playwright-python:v2

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set working directory
WORKDIR /app

# Copy your application code
COPY . .

# Command to run your application
CMD ["python", "api.py"]