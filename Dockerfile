# Use an official Python runtime as the base image
FROM python:3.9-slim-buster

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN apt-get update && apt-get install -y --no-cache-dir \
    build-essential \
    && pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Make the entrypoint.sh executable
RUN chmod +x entrypoint.sh

# Run entrypoint.sh when the container launches
ENTRYPOINT ["/app/entrypoint.sh"]
