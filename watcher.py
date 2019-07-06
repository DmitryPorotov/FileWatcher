import json
from path_watcher import PathWatcher
from db_handler import DbHandler
from pathlib import Path
from ssh_client import SshClient
import signal

db = None
ssh_clients = []


def main():
    conf = read_config()
    path_watchers = []
    global db
    db = DbHandler()
    for c in conf['sync']:
        ssh_clients.append(SshClient(c['server'], c['dirs']['to'], c['dirs']['from'], c['key_file']))
        path_watchers.append(PathWatcher(c['dirs']['from'],
                                         ssh_clients[-1],
                                         db))
    signal.signal(signal.SIGINT, clean_up)
    signal.signal(signal.SIGTERM, clean_up)


def clean_up():
    db.close()
    for c in ssh_clients:
        c.close()
    exit(0)


def read_config():
    try:
        conf = json.load(open(str(Path.home()) + '/.local/share/FileWatcher/config.json', 'r'))
    except IOError:
        o = {
            'sync': [{
                'server': '',
                'dirs': {
                    'from': '',
                    'to': ''
                }
            }]
        }
        p = Path(str(Path.home()) + '/.local/share/FileWatcher/')
        p.mkdir(exist_ok=True)
        fd = open(str(Path.home()) + '/.local/share/FileWatcher/config.json', 'w+')
        json.dump(o, fd)
        print('Please configure directories to sync at ~/.local/share/FileWatcher/config.json')
        exit(1)

    return conf


if __name__ == "__main__":
    main()
