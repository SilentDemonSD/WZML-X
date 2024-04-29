import os
import re
from anytree import NodeMixin, RenderTree
from typing import List, Tuple, Dict, Any

DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', '/usr/src/app/downloads/')
if not DOWNLOAD_DIR.endswith('/'):
    DOWNLOAD_DIR += '/'

class TorNode(NodeMixin):
    def __init__(self, name: str, is_folder: bool = False, is_file: bool = False, parent: 'TorNode' = None, size: int = None, priority: int = None, file_id: str = None, progress: float = None):
        super().__init__()
        self.name = name
        self.is_folder = is_folder
        self.is_file = is_file

        if parent is not None:
            self.parent = parent
        if size is not None:
            self.size = size
        if priority is not None:
            self.priority = priority
        if file_id is not None:
            self.file_id = file_id
        if progress is not None:
            self.progress = progress

def qb_get_folders(path: str) -> List[str]:
    return path.split('/')[1:] if path else []

def get_folders(path: str) -> List[str]:
    fs = re.findall(f'{DOWNLOAD_DIR}[0-9]+/(.+)', path)[0]
    return fs.split('/')

def make_tree(res: List[Any], aria2: bool = False) -> TorNode:
    parent = TorNode("Torrent")
    for i in res:
        folders = qb_get_folders(i.name) if not aria2 else get_folders(i['path'])
        current_node = parent
        for folder in folders:
            new_node = next((k for k in current_node.children if k.name == folder), None)
            if new_node is None:
                new_node = TorNode(folder, parent=current_node, is_folder=True)
            current_node = new_node

        if not aria2:
            TorNode(folders[-1], is_file=True, parent=current_node, size=i.size, priority=i.priority, file_id=i.id, progress=round(i.progress*100, 5))
        else:
            priority = 1 if i['selected'] == 'true' else 0
            TorNode(folders[-1], is_file=True, parent=current_node, size=i['length'], priority=priority, file_id=i['index'], progress=round((int(i['completedLength'])/int(i['length']))*100, 5))
    return parent

def create_list(par: TorNode, msg: Tuple[str, int]) -> str:
    html = msg[0]
    index = msg[1]

    if par.name != ".unwanted":
        html += '<ul>'
    for i in par.children:
        if i.is_folder:
            html += "<li>"
            if i.name != ".unwanted":
                html += f'<input type="checkbox" name="foldernode_{index}"> <label for="{i.name}">{i.name}</label>'
            html = create_list(i, (html, index + 1))
            html += "</li>"
        else:
            html += '<li>'
            if i.priority == 0:
                html += f'<input type="checkbox" name="filenode_{i.file_id}" data-size="{i.size}"> <label data-size="{i.size}" for="filenode_{i.file_id}">{i.name}</label> / {i.progress}%'
            else:
                html += f'<input type="checkbox" checked name="filenode_{i.file_id}" data-size="{i.size}"> <label data-size="{i.size}" for="filenode_{i.file_id}">{i.name}</label> / {i.progress}%'
            html += f'<input type="hidden" value="off" name="filenode_{i.file_id}">'
            html += "</li>"

    if par.name != ".unwanted":
        html += "</ul>"
    return html

