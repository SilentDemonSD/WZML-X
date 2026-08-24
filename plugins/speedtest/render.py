from bot.helper.ext_utils.status_utils import get_readable_file_size


def format_result(result):
    server = result.get("server") or {}
    return f"""
➲ <b><i>SPEEDTEST INFO</i></b>
┠ <b>Upload:</b> <code>{get_readable_file_size(result["upload"] / 8)}/s</code>
┠ <b>Download:</b>  <code>{get_readable_file_size(result["download"] / 8)}/s</code>
┠ <b>Ping:</b> <code>{result["ping"]} ms</code>
┠ <b>Time:</b> <code>{result["timestamp"]}</code>
┠ <b>Data Sent:</b> <code>{get_readable_file_size(int(result["bytes_sent"]))}</code>
┖ <b>Data Received:</b> <code>{get_readable_file_size(int(result["bytes_received"]))}</code>

➲ <b><i>SPEEDTEST SERVER</i></b>
┠ <b>Name:</b> <code>{server.get("name")}</code>
┠ <b>Country:</b> <code>{server.get("country")}, {server.get("cc")}</code>
┠ <b>Sponsor:</b> <code>{server.get("sponsor")}</code>
┠ <b>Latency:</b> <code>{server.get("latency")}</code>
┠ <b>Latitude:</b> <code>{server.get("lat")}</code>
┖ <b>Longitude:</b> <code>{server.get("lon")}</code>
"""
