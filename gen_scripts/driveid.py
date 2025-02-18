from os import path
from re import match

def main():
    info = (
        "\n\n"
        "        Bot can search files recursively, but you have to add the list of drives you want to search.\n"
        "        Use the following format: (You can use 'root' in the ID in case you want to use main drive.)\n"
        "        teamdrive NAME      -->   anything that you like\n"
        "        teamdrive ID        -->   id of teamdrives in which you like to search ('root' for main drive)\n"
        "        teamdrive INDEX URL -->   enter index url for this drive.\n"
        "                                  go to the respective drive and copy the url from address bar\n"
    )
    print(info)
    msg = ""
    filename = "list_drives.txt"

    if path.exists(filename):
        try:
            with open(filename, "r") as f:
                lines = f.read()
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            lines = ""
        if lines and not match(r"^\s*$", lines):
            print(lines)
            print(
                "\n\n"
                "      DO YOU WISH TO KEEP THE ABOVE DETAILS THAT YOU PREVIOUSLY ADDED? ENTER (y/n)\n"
                "      IF NOTHING SHOWS ENTER n"
            )
            while True:
                choice = input().strip()
                if choice.lower() == "y":
                    msg = lines
                    break
                elif choice.lower() == "n":
                    break
                else:
                    print(
                        "\n\n      Invalid input. Please enter 'y' for yes or 'n' for no."
                    )
    while True:
        try:
            num = int(input("    How Many Drive/Folder You Like To Add : "))
            break
        except ValueError:
            print("    Invalid number. Please enter an integer.")

    for count in range(1, num + 1):
        print(f"\n        > DRIVE - {count}\n")
        name = input("    Enter Drive NAME  (anything)     : ").strip()
        drive_id = input("    Enter Drive ID                   : ").strip()
        index = input("    Enter Drive INDEX URL (optional) : ").strip()

        if not name or not drive_id:
            print("\n\n        ERROR: Don't leave the name/ID empty.")
            exit(1)
        name = name.replace(" ", "_")
        if index:
            index = index.rstrip("/")
        else:
            index = ""
        msg += f"{name} {drive_id} {index}\n"

    try:
        with open(filename, "w") as file:
            file.write(msg)
    except Exception as e:
        print(f"Error writing to {filename}: {e}")
        exit(1)
    print("\n\n    Done!")

if __name__ == "__main__":
    main()
