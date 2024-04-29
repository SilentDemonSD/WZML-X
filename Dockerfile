FROM anasty17/mltb:latest

WORKDIR /usr/src/app

# There's no need to give execute permissions to the entire app directory
# RUN chmod 777 /usr/src/app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# It's recommended to run updates and upgrades before installing any packages
RUN apt-get update && apt-get upgrade -y

# Use apt-get install instead of apt for better error messages
RUN apt-get install -y --no-install-recommends mediainfo

# Only copy the necessary files to reduce the image size
COPY . .

# Use exec to replace the current shell with the new command
CMD ["exec", "bash", "start.sh"]
