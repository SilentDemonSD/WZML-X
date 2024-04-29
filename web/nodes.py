import os
import re
from typing import List, Any, Tuple, Dict

from anytree import NodeMixin

DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', '/usr/src/app/downloads/')
if DOWNLOAD_DIR[-1] != '/':
    DOWNLOAD_DIR += '/'


class TorNode(NodeMixin):
    def __init__(self, name: str, is_folder: bool = False, is_file: bool = False, parent: Any = None, size: int = None,
                 priority: int = None, file_id: int = None, progress: float = None):
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
    """
    Split the path into folders
    """
    return path.split("/")


def get_folders(path: str) -> List[str]:
    """
    Find all folders in the path
    """
    fs = re.findall(f'{DOWNLOAD_DIR}[0-9]+/(.+)', path)[0]
    return fs.split('/')


def make_tree(res: List[Any], aria2: bool = False) -> TorNode:
    """
    Create a tree of TorNode objects from the input list
    """
    if not res:
        raise ValueError("Input list is empty")

    parent = TorNode("Torrent")
    for i in res:
        if aria2:
            folders = get_folders(i['path'])
            priority = 1
            if i['selected'] == 'false':
                priority = 0
        else:
            folders = qb_get_folders(i.name)

        if len(folders) > 1:
            previous_node = parent
            for j in range(len(folders) - 1):
                current_node = next((k for k in previous_node.children if k.name == folders[j]), None)
                if current_node is None:
                    previous_node = TorNode(folders[j], parent=previous_node, is_folder=True)
                else:
                    previous_node = current_node
            TorNode(folders[-1], is_file=True, parent=previous_node, size=get_size(i), priority=priority,
                    file_id=get_file_id(i), progress=get_progress(i))
        else:
            TorNode(folders[-1], is_file=True, parent=parent, size=get_size(i), priority=priority,
                    file_id=get_file_id(i), progress=get_progress(i))
    return parent


def get_size(i) -> int:
    if isinstance(i, dict):
        return i.get('length', 0)
    elif hasattr(i, 'size'):
        return i.size
    else:
        return 0


def get_file_id(i) -> int:
    if isinstance(i, dict):
        return i.get('index', 0)
    elif hasattr(i, 'file_id'):
        return i.file_id
    else:
        return 0


def get_progress(i) -> float:
    if isinstance(i, dict):
        completed_length = i.get('completedLength', 0)
        length = i.get('length', 1)
        return completed_length / length * 100
    elif hasattr(i, 'progress'):
        return i.progress
    else:
        return 0


def create_list(par: TorNode, msg: Tuple[str, int]) -> Tuple[str, int]:
    """
    Create an HTML list from the tree of TorNode objects
    """
    if par.name != ".unwanted":
        msg = (msg[0] + '<ul>', msg[1] + 1)
    for i in par.children:
        if i.is_folder:
            msg = create_list(i, msg)
        else:
            msg = add_file_node(i, msg)
    if par.name != ".unwanted":
        msg = (msg[0] + "</ul>", msg[1])
    return msg


def add_file_node(i: TorNode, msg: Tuple[str, int]) -> Tuple[str, int]:
    """
    Add a file node to the HTML list
    """
    if i.priority == 0:
        checked = ""
    else:
        checked = "checked"

    msg = (msg[0] + f'<li><input type="checkbox" name="filenode_{i.file_id}" {checked} data-size="{i.size}"> '
           f'<label data-size="{i.size}" for="filenode_{i.file_id}">{i.name}</label> / {i.progress}%'
           f'<input type="hidden" value="off" name="filenode_{i.file_id}"></li>', msg[1])
    return msg


def print_tree(parent):
    """
    Print the tree of TorNode objects
    """
    for pre, _, node in RenderTree(parent):
        treestr = u"%s%s" % (pre, node.name)
        print(treestr.ljust(8), node.is_folder, node.is_file)
