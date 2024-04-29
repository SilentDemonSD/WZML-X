import os
import anytree
from anytree import NodeMixin
from typing import List, Optional

DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', '')
if not DOWNLOAD_DIR:
    raise ValueError('DOWNLOAD_DIR environment variable is not set')
DOWNLOAD_DIR = os.path.join(DOWNLOAD_DIR, '')


class TorNode(NodeMixin):
    def __init__(self, name: str, is_folder: bool = False, is_file: bool = False, parent: Optional['TorNode'] = None, size: Optional[int] = None, priority: Optional[int] = None, file_id: Optional[str] = None, progress: Optional[float] = None):
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

    def __str__(self):
        if self.is_folder:
            return f'{self.name}/'
        else:
            return f'{self.name} ({self.size} bytes, {self.progress}%)'


def qb_get_folders(path: str) -> List[str]:
    return path.split('/')


def get_folders(path: str) -> List[str]:
    folders = []
    while path != '/':
        path, folder = os.path.split(path)
        folders.append(folder)
    return folders[::-1]


def make_tree(res: List) -> TorNode:
    parent = TorNode("Torrent")
    if res:
        for i in res:
            folders = get_folders(i.name) if isinstance(i, TorNode) else get_folders(i['path'])
            previous_node = parent
            for j in folders:
                current_node = next((k for k in previous_node.children if k.name == j), None)
                if current_node is None:
                    current_node = TorNode(j, parent=previous_node, is_folder=True)
                previous_node = current_node
            if isinstance(i, TorNode):
                TorNode(i.name, is_file=i.is_file, parent=previous_node, size=i.size, priority=i.priority, file_id=i.file_id, progress=i.progress)
            else:
                TorNode(folders[-1], is_file=True, parent=previous_node, size=i['length'], priority=1 if i['selected'] == 'true' else 0, file_id=i['index'], progress=round((int(i['completedLength'])/int(i['length']))*100, 5))
    return parent


def create_list(par: TorNode, level: int = 0) -> str:
    result = ''
    if par.name != ".unwanted":
        result += '<ul>'
    for i in par.children:
        if i.is_folder:
            result += f'<li><input type="checkbox" name="foldernode_{level}"> <label for="{i.name}">{i.name}</label>'
            result = create_list(i, level=level+1) + result
            result += '</li>'
        else:
            result += f'<li><input type="checkbox" {"" if i.priority == 0 else "checked"} name="filenode_{i.file_id}" data-size="{i.size}"> <label data-size="{i.size}" for="filenode_{i.file_id}">{i.name}</label> / {i.progress}%'
            result += f'<input type="hidden" value="off" name="filenode_{i.file_id}">'
            result += '</li>'
    if par.name != ".unwanted":
        result += '</ul>'
    return result
