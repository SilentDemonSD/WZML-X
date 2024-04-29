from pyrogram import Client, __version__

print(f'Required pyrogram version {__version__} or greater.')
if int(__version__.split('.')[0]) < 2:
    raise Exception("Pyrogram version 2 or greater is required.")

API_KEY = int(input("Enter API KEY: "))
API_HASH = input("Enter API HASH: ")

with Client(name='USS', api_id=API_KEY, api_hash=API_HASH, in_memory=True) as app:
    print(f'Session string: \n{app.export_session_string()}')
