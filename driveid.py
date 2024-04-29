import os
import re
import argparse

def validate_input(prompt: str, valid_inputs: tuple) -> str:
    """Validate user input and re-prompt if invalid."""
    while True:
        user_input = input(prompt).rstrip()
        if user_input in valid_inputs:
            return user_input
        print(f"Invalid input. Please enter one of the following: {', '.join(valid_inputs)}")

def read_drives_file(file_path: str) -> str:
    """Read drives file and return its content."""
    if not os.path.exists(file_path):
        return ""
    with open(file_path, 'r') as f:
        return f.read()

def write_drives_file(file_path: str, drives: str) -> None:
    """Write drives to the drives file."""
    with open(file_path, 'w') as f:
        f.write(drives)

def main() -> None:
    """Main function to manage drives."""
    parser = argparse.ArgumentParser(description="Manage drives for file search.")
    parser.add_argument("--list", action="store_true", help="List previously added drives.")
    args = parser.parse_args()

    file_path = os.path.expanduser("~/list_drives.txt")
    drives = read_drives_file(file_path)

    if args.list:
        print(f"Previously added drives:\n{drives}")
        return

    print("""
        Bot can search files recursively, but you have to add the list of drives you want to search.
        Use the following format:
            teamdrive NAME      -->   anything that you likes
            teamdrive ID        -->   id of teamdrives in which you likes to search ('root' for main drive)
            teamdrive INDEX URL -->   enter index url for this drive.
                                      go to the respective drive and copy the url from address bar
        """)

    if drives:
        print("\n\n  DO YOU WISH TO KEEP THE ABOVE DETAILS THAT YOU PREVIOUSLY ADDED??? (y/n)")
        if validate_input("\n  ", ("y", "Y", "n", "N")) in ["n", "N"]:
            drives = ""

    num_drives = int(validate_input("  How many drives/folders would you like to add: ", ("1", "2", "3", "4", "5")))

    for i in range(1, num_drives + 1):
        print(f"\n  > DRIVE - {i}\n")
        name = validate_input("    Enter drive NAME (anything): ", ("",))
        id_ = validate_input("    Enter drive ID: ", ("",))
        index = input("    Enter drive INDEX URL (optional): ")
        if index:
            index = index.rstrip("/")
        drive = f"{name} {id_} {index}\n"
        drives += drive

    write_drives_file(file_path, drives)
    print("\n\n  Done!")

if __name__ == "__main__":
    main()
