import os
import re
import urllib.parse

print(
    "\n\n"
    "        Bot can search files recursively, but you have to add the list of drives you want to search.\n"
    "        Use the following format:\n"
    "        teamdrive NAME      -->   anything that you likes\n"
    "        teamdrive ID        -->   id of teamdrives in which you likes to search ('root' for main drive)\n"
    "        teamdrive INDEX URL -->   enter index url for this drive.\n"
    "                                  go to the respective drive and copy the url from address bar\n")
# The function reads the contents of a file and returns it as a string
def read_file(file_path: str) -> str:
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return f.read()
    else:
        return ""

# The function writes the given message to the file
def write_file(file_path: str, msg: str) -> None:
    with open(file_path, 'w') as file:
        file.write(msg)

# The function checks if the given url is a valid url
def is_valid_url(url: str) -> bool:
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

# Read the contents of the list_drives.txt file
msg = read_file('list_drives.txt')

# Print the contents of the list_drives.txt file
if msg:
    print(msg)
    print(
        "\n\n"
        "      DO YOU WISH TO KEEP THE ABOVE DETAILS THAT YOU PREVIOUSLY ADDED???? ENTER (y/n)\n"
        "      IF NOTHING SHOWS ENTER n")
# Get user input to decide whether to keep the previous details or not
while True:
    choice = input()
    if choice in ['y', 'Y']:
        break
    elif choice in ['n', 'N']:
        msg = ""
        break
    else:
        print(
            "\n\n      DO YOU WISH TO KEEP THE ABOVE DETAILS ???? y/n <=== this is option ..... OPEN YOUR EYES & READ...")

# Get the number of drives/folders the user wants to add
num = int(input("    How Many Drive/Folder You Likes To Add : "))

# Loop through the given range to get the details of each drive/folder
for count in range(1, num + 1):
    print(f"\n        > DRIVE - {count}\n")
    # Get the name of the drive
    name = input("    Enter Drive NAME  (anything)     : ")
    # Get the id of the drive
    id = input("    Enter Drive ID                   : ")
    # Get the index url of the drive
    index = input("    Enter Drive INDEX URL (optional) : ")
    # Check if the name and id are empty or not
    if not name or not id:
        print("\n\n        ERROR : Dont leave the name/id without filling.")
        exit(1)
    # Replace spaces in the name with underscores
    name = name.replace(" ", "_")
    # Check if the index url is valid or not
    if index and not is_valid_url(index):
        print("\n\n        ERROR : Invalid URL format.")
        exit(1)
    # Append the details of the drive to the message
    msg += f"{name} {id} {index}\n"

# Write the message to the list_drives.txt file
write_file('list_drives.txt', msg)
print("\n\n    Done!")

