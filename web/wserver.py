from logging import getLogger, FileHandler, StreamHandler, INFO, basicConfig
from time import sleep
from qbittorrentapi import NotFound404Error, Client as qbClient
from aria2p import API as ariaAPI, Client as ariaClient
from flask import Flask, request, abort, render_template
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
    return render_template('homepage.html')

@app.errorhandler(Exception)
def page_not_found(e):
    return f"<h1>404: Torrent not found! Mostly wrong input. <br><br>Error: {e}</h2>", 404

@app.route('/app/files/<string:id_>?pin_code=<string:pin_code>')
def list_torrent_contents(id_, pin_code):
    if not validate_pin_code(id_, pin_code):
        return "<h1>Incorrect pin code</h1>"

    if len(id_) > 20:
        with qbClient(host="localhost", port="8090") as client:
            try:
                res = client.torrents_files(torrent_hash=id_)
                cont = make_tree(res)
            except NotFound404Error:
                return abort(404)
            client.auth_log_out()
    else:
        try:
            res = aria2.client.get_files(id_)
            cont = make_tree(res, True)
        except KeyError:
            return abort(404)

    return render_template('list_torrent_contents.html', My_content=cont[0], form_url=f"/app/files/{id_}?pin_code={pin_code}")

def set_priority(id_, pin_code):
    if not validate_pin_code(id_, pin_code):
        return "<h1>Incorrect pin code</h1>"

    # Add code to set priority here

    return "<h1>Priority set successfully</h1>"

def validate_pin_code(id_, pin_code):
    pincode = ""
    for nbr in id_:
        if nbr.isdigit():
            pincode += str(nbr)
        if len(pincode) == 4:
            break

    return request.args.get("pin_code") == pincode


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
        {{ My_content }}
        <a href="{{ form_url }}" style="text-decoration: none;">
            <button class="button">Set Priority</button>
        </a>
    </div>
    <div class="footer">
© 2022-23 WZML-X. All Rights Reserved.
    </div>
</body>
</html>
