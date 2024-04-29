# Use an official Python runtime as the base image
FROM python:3.9-slim-buster as builder

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file to the working directory and install packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    rm requirements.txt

# Copy the rest of the application code
COPY . .

# Build a separate stage for production
FROM python:3.9-slim-buster

# Set the working directory to /app
WORKDIR /app

# Copy only the necessary files for production
COPY --from=builder /app /app

# Make the entrypoint.sh executable and set it as the container's default command
COPY --from=builder /app/entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]

# Add a CMD instruction to specify the default command to run when the container starts
CMD ["python", "app.py"]

# Include a .dockerignore file to exclude unnecessary files from the build context
# This can help reduce the build time and the size of the final image
echo "*pyc" > .dockerignore
echo "*/__pycache__" >> .dockerignore
