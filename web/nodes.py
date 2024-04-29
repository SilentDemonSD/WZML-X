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

        self.parent = parent
        self.size = size
        self.priority = priority
        self.file_id = file_id
        self.progress = progress

def qb_get_folders(path: str) -> List[str]:
    return path.split('/')[1:] if path else []

def get_folders(path: str) -> List[str]:
    fs = re.findall(f'{DOWNLOAD_DIR}[0-9]+/(.+)', path)[0]
    return fs.split('/')

def make_tree(res: List['Dict[str, Any]'], aria2: bool = False) -> 'TorNode':
    parent = TorNode("Torrent")
    for i in res:
        folders = qb_get_folders(i.get('name')) if aria2 else get_folders(i['path'])
        current_node = parent
        for folder in folders:
            next_node = next((k for k in current_node.children if k.name == folder), None)
            if next_node is None:
                next_node = TorNode(folder, parent=current_node, is_folder=True)
            current_node = next_node

        file_node = TorNode(folders[-1], is_file=True, parent=current_node)
        if aria2:
            file_node.size = i['length']
            file_node.priority = 1 if i['selected'] == 'true' else 0
            file_node.progress = (int(i['completedLength']) / int(i['length'])) * 100
        else:
            file_node.size = i.size
            file_node.priority = i.priority
            file_node.progress = round(i.progress * 100, 5)

    return parent

def create_list(par: 'TorNode', msg: Tuple[str, int]) -> Tuple[str, int]:
    if par.name != ".unwanted":
        msg = (msg[0] + '<ul>', msg[1] + 1)
    for i in par.children:
        if i.is_folder:
            msg = create_list(i, msg)
            if i.name != ".unwanted":
                msg = (msg[0] + f'<li><input type="checkbox" name="foldernode_{msg[1]}"> <label for="{i.name}">{i.name}</label></li>', msg[1])
        else:
            msg = (msg[0] + f'<li><input type="checkbox" {"" if i.priority == 0 else "checked"} name="filenode_{i.file_id}" data-size="{i.size}"> <label data-size="{i.size}" for="filenode_{i.file_id}">{i.name}</label> / {i.progress}%<input type="hidden" value="off" name="filenode_{i.file_id}"></li>', msg[1])

    if par.name != ".unwanted":
        msg = (msg[0] + "</ul>", msg[1])
    return msg

def print_tree(parent):
    for pre, _, node in RenderTree(parent):
        treestr = u"%s%s" % (pre, node.name)
        print(treestr.ljust(8), node.is_folder, node.is_file)
