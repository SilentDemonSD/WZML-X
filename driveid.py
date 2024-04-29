import os
import re
import urllib.parse

def read_file(file_path: str) -> str:
    """Read the contents of a file and returns it as a string."""
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return ""

def write_file(file_path: str, msg: str) -> None:
    """Write the given message to the file."""
    with open(file_path, 'w') as file:
        file.write(msg)

def is_valid_url(url: str) -> bool:
    """Check if the given url is a valid url."""
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

def is_empty(string: str) -> bool:
    """Check if the given string is empty or not."""
    return not bool(string)

def replace_spaces(string: str) -> str:
    """Replace spaces in the given string with underscores."""
    return string.replace(" ", "_")

def is_valid_index_url(index: str, is_url_required: bool) -> bool:
    """Check if the given index url is valid or not."""
    if is_url_required and index:
        return is_valid_url(index)
    return True

def add_drive_details() -> str:
    """Add the details of the drive and return it as a string."""
    name = input("    Enter Drive NAME (anything): ")
    id = input("    Enter Drive ID: ")
    index = input("    Enter Drive INDEX URL (optional): ")

    if not is_empty(name) and not is_empty(id):
        name = replace_spaces(name)
        if is_valid_index_url(index, bool(index)):
            return f"{name} {id} {index}\n"
        else:
            print("\n\n        ERROR: Invalid URL format.")
            return ""
    else:
        print("\n\n        ERROR: Don't leave the name/id without filling.")
        return ""

def main() -> None:
    print(
        "\n\n"
        "        Bot can search files recursively, but you have to add the list of drives you want to search.\n"
        "        Use the following format:\n"
        "        teamdrive NAME      -->   anything that you likes\n"
        "        teamdrive ID        -->   id of teamdrives in which you likes to search ('root' for main drive)\n"
        "        teamdrive INDEX URL -->   enter index url for this drive.\n"
        "                                  go to the respective drive and copy the url from address bar\n")

    msg = read_file('list_drives.txt')
    print(msg)

    if input("\n      DO YOU WISH TO KEEP THE ABOVE DETAILS THAT YOU PREVIOUSLY ADDED???? ENTER (y/n)\n      IF NOTHING SHOWS ENTER n: ").lower() not in ['y', 'yes']:
        msg = ""

    num = int(input("    How Many Drive/Folder You Likes To Add: "))

    for count in range(1, num + 1):
        print(f"\n        > DRIVE - {count}\n")
        drive_details = add_drive_details()
        if drive_details:
            msg += drive_details

    write_file('list_drives.txt', msg)

if __name__ == '__main__':
    main()
