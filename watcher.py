import json
from path_watcher import PathWatcher
from db_handler import DbHandler

def main():
    conf = read_config()
    path_watchers = []
    db = DbHandler()
    for c in conf['sync']:
        path_watchers.append(PathWatcher(c['dirs']['from'], c['dirs']['to'], c['server'], db))


def read_config():
    conf = json.load(open('config.json', 'r'))
    return conf


if __name__ == "__main__":
    main()
