# Use an official Python runtime as a parent image
FROM python:3.10-slim-bookworm

# Set the working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application into the container
COPY tickr .

CMD ["python", "-m", "strategies.fibonnaci.retracement"]

