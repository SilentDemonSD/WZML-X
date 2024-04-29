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

def read_file(file_path: str) -> str:
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return f.read()
    else:
        return ""

def write_file(file_path: str, msg: str) -> None:
    with open(file_path, 'w') as file:
        file.write(msg)

def is_valid_url(url: str) -> bool:
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

msg = read_file('list_drives.txt')

if msg:
    print(msg)
    print(
        "\n\n"
        "      DO YOU WISH TO KEEP THE ABOVE DETAILS THAT YOU PREVIOUSLY ADDED???? ENTER (y/n)\n"
        "      IF NOTHING SHOWS ENTER n")
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

num = int(input("    How Many Drive/Folder You Likes To Add : "))
for count in range(1, num + 1):
    print(f"\n        > DRIVE - {count}\n")
    name = input("    Enter Drive NAME  (anything)     : ")
    id = input("    Enter Drive ID                   : ")
    index = input("    Enter Drive INDEX URL (optional) : ")
    if not name or not id:
        print("\n\n        ERROR : Dont leave the name/id without filling.")
        exit(1)
    name = name.replace(" ", "_")
    if index and not is_valid_url(index):
        print("\n\n        ERROR : Invalid URL format.")
        exit(1)
    msg += f"{name} {id} {index}\n"

write_file('list_drives.txt', msg)
print("\n\n    Done!")
