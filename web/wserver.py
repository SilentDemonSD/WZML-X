from logging import getLogger, FileHandler, StreamHandler, INFO, basicConfig
from time import sleep
from qbittorrentapi import NotFound404Error, Client as qbClient
from aria2p import API as ariaAPI, Client as ariaClient
from flask import Flask, request, abort

from web.nodes import make_tree

app = Flask(__name__)

def init_app():
    global aria2

    basicConfig(format="[%(asctime)s] [%(levelname)s] - %(message)s",
                datefmt="%d-%b-%y %I:%M:%S %p",
                handlers=[FileHandler('log.txt'), StreamHandler()],
                level=INFO)

    LOGGER = getLogger(__name__)

    aria2 = ariaAPI(ariaClient(host="http://localhost", port=6800, secret=""))

    @app.route('/')
    def homepage():
        return """
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
"""

    @app.errorhandler(Exception)
    def page_not_found(e):
        return f"<h1>404: Torrent not found! Mostly wrong input. <br><br>Error: {e}</h2>", 404

    @app.route('/app/files/<string:id_>', methods=['GET'])
    def list_torrent_contents(id_):

        if "pin_code" not in request.args.keys():
            return code_page.replace("{form_url}", f"/app/files/{id_}")

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
        return page.replace("{My_content}", cont[0]).replace("{form_url}", f"/app/files/{id_}?pin_code={pincode}")


    @app.route('/app/files/<string:id_>', methods=['POST'])
    def set_priority(id_):

        data = dict(request.form)
        resume = ""
        if len(id_) > 20:
            pause = ""

            for i, value in data.items():
                if "filenode" in i:
                    node_no = i.split("_")[-1]

                    if value == "on":
                        resume += f"{node_no}|"
                    else:
                        pause += f"{node_no}|"

            pause = pause.strip("|")
            resume = resume.strip("|")

            with qbClient(host="localhost", port="8090") as client:

                try:
                    client.torrents_file_priority(
                        torrent_hash=id_, file_ids=pause, priority=0)
                except NotFound404Error as e:
                    raise NotFound404Error from e
                except Exception as e:
                    LOGGER.error(f"{e} Errored in paused")
                try:
                    client.torrents_file_priority(
                        torrent_hash=id_, file_ids=resume, priority=1)
                except NotFound404Error as e:
                    raise NotFound404Error from e
                except Exception as e:
                    LOGGER.error(f"{e} Errored in resumed")
                sleep(1)
                if not re_verfiy(pause, resume, client, id_):
                    LOGGER.error(f"Verification Failed! Hash: {id_}")
                client.auth_log_out()
        else:
            for i, value in data.items():
                if "filenode" in i and value == "on":
                    node_no = i.split("_")[-1]
                    resume += f'{node_no},'

            resume = resume.strip(",")

            try:
                res = aria2.client.change_option(id_, {'select-file': resume})
            except aria2p.exceptions.ClientError as e:
                if e.args[0] == "Invalid GID":
                    abort(404)
                else:
                    raise

            if res == "OK":
                LOGGER.info(f"Verified! GID: {id_}")
            else:
                LOGGER.info(f"Verification Failed! Report! GID: {id_}")
        return list_torrent_contents(id_)

if __name__ == "__main__":
    init_app()
    app.run(debug=True)
