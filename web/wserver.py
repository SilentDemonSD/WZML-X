from logging import getLogger, FileHandler, StreamHandler, INFO, basicConfig
from time import sleep
from qbittorrentapi import NotFound404Error, Client as qbClient
from aria2p import API as ariaAPI, Client as ariaClient
from flask import Flask, request, abort, render_template_string

from web.nodes import make_tree

app = Flask(__name__)

def init_app():
    basicConfig(format="[%(asctime)s] [%(levelname)s] - %(message)s",
                datefmt="%d-%b-%y %I:%M:%S %p",
                handlers=[FileHandler('log.txt'), StreamHandler()],
                level=INFO)

    global aria2

    aria2 = ariaAPI(ariaClient(host="http://localhost", port=6800, secret=""))

@app.route('/')
def homepage():
    return render_template_string("""
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link
      href="https://fonts.googleapis.com/css2?family=Ubuntu:ital,wght@0,300;0,400;0,500;0,700;1,300;1,400;1,500;1,700&display=swap"
      rel="stylesheet"
    />
    <link rel="icon" href="https://graph.org/file/1a6ad157f55bc42b548df.png" type="image/jpg">
    <style>
        body {
            background-color: #0D1117;
            color: white;
            font-family: "Ubuntu", sans-serif;
        }
        .header {
            background-color: black;
            text-align: center;
            width: 100%;
            padding: 1px;
        }
        .footer {
            background-color: black;
            padding: 10px;
            text-align: center;
            position: absolute;
            bottom: 0;
            width: 100%;
        }
        .content {
            padding: 20px;
            text-align: center;
        }
        .button {
            background-color: #0001f0;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .image {
            border-radius: 12px;
            max-width: 100%;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>WZML-X</h1>
    </div>
    <div class="content">
        <img src="https://graph.org/file/639fe4239b78e5862b302.jpg" class="image">
        <a href="https://telegram.me/WZML_X" style="text-decoration: none;">
            <button class="button">Join Updates Channel Now</button>
        </a>
    </div>
    <div class="footer">
© 2022-23 WZML-X. All Rights Reserved.
    </div>
</body>
</html>
""")

@app.errorhandler(Exception)
def page_not_found(e):
    return f"<h1>404: Torrent not found! Mostly wrong input. <br><br>Error: {e}</h2>", 404

def list_torrent_contents(id_, pin_code):
    if "pin_code" not in request.args.keys():
        return render_template_string("""
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link
      href="https://fonts.googleapis.com/css2?family=Ubuntu:ital,wght@0,300;0,400;0,500;0,700;1,300;1,400;1,500;1,700&display=swap"
      rel="stylesheet"
    />
    <link rel="icon" href="https://graph.org/file/1a6ad157f55bc42b548df.png" type="image/jpg">
    <style>
        body {
            background-color: #0D1117;
            color: white;
            font-family: "Ubuntu", sans-serif;
        }
        .header {
            background-color: black;
            text-align: center;
            width: 100%;
            padding: 1px;
        }
        .footer {
            background-color: black;
            padding: 10px;
            text-align: center;
            position: absolute;
            bottom: 0;
            width: 100%;
        }
        .content {
            padding: 20px;
            text-align: center;
        }
        .button {
            background-color: #0001f0;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .image {
            border-radius: 12px;
            max-width: 100%;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>WZML-X</h1>
    </div>
    <div class="content">
        <img src="https://graph.org/file/639fe4239b78e5862b302.jpg" class="image">
        <a href="https://telegram.me/WZML_X" style="text-decoration: none;">
            <button class="button">Join Updates Channel Now</button>
        </a>
    </div>
    <div class="footer">
© 2022-23 WZML-X. All Rights Reserved.
    </div>
</body>
</html>
""", form_url=f"/app/files/{id_}")

    pincode = ""
    for nbr in id_:
        if nbr.isdigit():
            pincode += str(nbr)
        if len(pincode) == 4:
            break

    if request.args["pin_code"] != pincode:
        return "<h1>Incorrect pin code</h1>"

    if len(id_) > 20:
        with qbClient(host="localhost", port="8090") as client:
            res = client.torrents_files(torrent_hash=id_)
            cont = make_tree(res)
            client.auth_log_out()
    else:
        res = aria2.client.get_files(id_)
        cont = make_tree(res, True)

    return render_template_string("""
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link
      href="https://fonts.googleapis.com/css2?family=Ubuntu:ital,wght@0,300;0,400;0,500;0,700;1,300;1,400;1,500;1,700&display=swap"
      rel="stylesheet"
    />
    <link rel="icon" href="https://graph.org/file/1a6ad157f55bc42b548df.png" type="image/jpg">
    <style>
        body {
            background-color: #0D1117;
            color: white;
            font-family: "Ubuntu", sans-serif;
        }
        .header {
            background-color: black;
            text-align: center;
            width: 100%;
            padding: 1px;
        }
        .footer {
            background-color: black;
            padding: 10px;
            text-align: center;
            position: absolute;
            bottom: 0;
            width: 100%;
        }
        .content {
            padding: 20px;
            text-align: center;
        }
        .button {
            background-color: #0001f0;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .image {
            border-radius: 12px;
            max-width: 100%;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>WZML-X</h1>
    </div>
    <div class="content">
        <img src="https://graph.org/file/639fe4239b78e5862b302.jpg" class="image">
        <a href="https://telegram.me/WZML_X" style="text-decoration: none;">
            <button class="button">Join Updates Channel Now</button>
        </a>
    </div>
    <div class="footer">
© 2022-23 WZML-X. All Rights Reserved.
    </div>
</body>
</html>
""", My_content=cont[0], form_url=f"/app/files/{id_}?pin_code={pincode}")

def set_priority(id_, pin_code):
    if "pin_code" not in request.args.keys():
        return render_template_string("""
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link
      href="https://fonts.googleapis.com/css2?family=Ubuntu:ital,wght@0,300;0,400;0,500;0,700;1,300;1,400;1,500;1,700&display=swap"
      rel="stylesheet"
    />
    <link rel="icon" href="https://graph.org/file/1a6ad157f55bc42b548df.png" type="image/jpg">
    <style>
        body {
            background-color: #0D1117;
            color: white;
            font-family: "Ubuntu", sans-serif;
        }
