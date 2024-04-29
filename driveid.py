import os
import re

print(
    "\n"
    "        Bot can search files recursively, but you have to add the list of drives you want to search.\n"
    "        Use the following format:\n"
    "        teamdrive NAME      -->   anything that you likes\n"
    "        teamdrive ID        -->   id of teamdrives in which you likes to search ('root' for main drive)\n"
    "        teamdrive INDEX URL -->   enter index url for this drive.\n"
    "                                  go to the respective drive and copy the url from address bar\n"
)

def get_user_choice(prompt: str) -> str:
    """Get user's y/n choice"""
    while True:
        choice = input(prompt).lower()
        if choice in ['y', 'n']:
            return choice
        else:
            print(
                "\n\n        DO YOU WISH TO KEEP THE ABOVE DETAILS ???? y/n <=== this is option ..... OPEN YOUR EYES & READ...")

def get_non_empty_input(prompt: str) -> str:
    """Get non-empty user input"""
    while True:
        input_str = input(prompt)
        if input_str:
            return input_str
        else:
            print("\n\n        ERROR : Dont leave the name/id without filling.")
            exit(1)

def read_drives_file(file_path: str) -> str:
    """Read the contents of the drives file"""
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            lines = f.read()
        if re.match(r'^\s*$', lines):
            return ''
        else:
            print(lines)
            return lines
    else:
        return ''

def write_drives_file(file_path: str, msg: str) -> None:
    """Write the drives file"""
    with open(file_path, 'w') as file:
        file.truncate(0)
        file.write(msg)

def main() -> None:
    drives_file = 'list_drives.txt'
    msg = read_drives_file(drives_file)

    if msg:
        keep_details = get_user_choice(
            "\n\n      DO YOU WISH TO KEEP THE ABOVE DETAILS THAT YOU PREVIOUSLY ADDED???? ENTER (y/n)\n      IF NOTHING SHOWS ENTER n")
        if keep_details == 'n':
            msg = ''

    num = int(get_non_empty_input("    How Many Drive/Folder You Likes To Add : "))

    for count in range(1, num + 1):
        print(f"\n        > DRIVE - {count}\n")
        name = get_non_empty_input("    Enter Drive NAME  (anything)     : ")
        id_ = get_non_empty_input("    Enter Drive ID                   : ")
        index = input("    Enter Drive INDEX URL (optional) : ")
        if index:
            if not index.endswith('/'):
                index += '/'
            msg += f"{name} {id_} {index}"
        else:
            msg += f"{name} {id_} {index}\n"

    write_drives_file(drives_file, msg)
    print("\n\n    Done!")

if __name__ == '__main__':
    main()
