# Use an official Python image as the base
FROM mcr.microsoft.com/playwright/python:v1.41.0

# Set the working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright dependencies and browsers
RUN playwright install --with-deps chromium

# Copy the entire application into the container
COPY . .

# Set the command to run the script
CMD ["python", "tradovate.py"]