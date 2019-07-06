from pathlib import Path


def resolve_home_dir(path, is_dir=False):
    if '~' in path:
        path = str(Path.home()) + path.split('~')[1]
    if is_dir:
        path += '/'
    return path
