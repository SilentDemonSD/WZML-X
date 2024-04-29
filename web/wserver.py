from logging import getLogger, FileHandler, StreamHandler, INFO, basicConfig
from time import sleep
from qbittorrentapi import NotFound404Error, Client as qbClient
from aria2p import API as ariaAPI, Client as ariaClient, RPCError
from flask import Flask, request, render_template
from web.nodes import make_tree

app = Flask(__name__)

aria2 = ariaAPI(ariaClient(host="http://localhost", port=6800, secret=""))

basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[FileHandler('log.txt'), StreamHandler()],
                    level=INFO)

LOGGER = getLogger(__name__)

@app.route('/app/files/<string:id_>', methods=['GET'])
def list_torrent_contents(id_):
    if "pin_code" not in request.args.keys():
        return render_template('code_page.html', form_url=f"/app/files/{id_}")

    pincode = ""
    for nbr in id_:
        if nbr.isdigit():
            pincode += str(nbr)
        if len(pincode) == 4:
            break
    if request.args["pin_code"] != pincode:
        return "<h1>Incorrect pin code</h1>"

    if len(id_) > 20:
        client = qbClient(host="localhost", port="8090")
        res = client.torrents_files(torrent_hash=id_)
        cont = make_tree(res)
        client.auth_log_out()
    else:
        res = aria2.client.get_files(id_)
        cont = make_tree(res, True)
    return render_template('page.html', My_content=cont[0], form_url=f"/app/files/{id_}?pin_code={pincode}")

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

        client = qbClient(host="localhost", port="8090")

        try:
            client.torrents_file_priority(torrent_hash=id_, file_ids=pause, priority=0)
        except NotFound404Error:
            raise NotFound404Error
        except Exception as e:
            LOGGER.error(f"{e} Errored in paused")
        try:
            client.torrents_file_priority(torrent_hash=id_, file_ids=resume, priority=
