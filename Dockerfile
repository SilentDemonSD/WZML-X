# Use an official Python runtime as the base image
FROM python:3.9-slim-buster

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file to the working directory and install packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Make the entrypoint.sh executable and set it as the container's default command
RUN chmod +x entrypoint.sh \
 && sed -i '1s/^/#!\/bin\/bash\n/' /app/entrypoint.sh \
 && sed -i '$s/$/&\nexit 0/' /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
