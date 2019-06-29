import inotify.adapters
from ssh_client import SshClient


class PathWatcher:
    _temp_files = ['___jb_old___', '___jb_tmp___']
    _synchronizable_events = ['IN_CREATE', 'IN_MOVED_TO', 'IN_DELETE', 'IN_MODIFY', 'IN_ATTRIB']

    def __init__(self, path_from, path_to, server, db):
        self.path_from = path_from
        self.path_to = path_to
        self.server = server
        self.db = db
        self.ssh = SshClient(server, path_to)
        self._start_watcher()

    def _start_watcher(self):
        i = inotify.adapters.InotifyTree(self.path_from)
        for evt in i.event_gen():
            if evt is not None and not self._is_temp_file(evt[3]) and self._is_sync_needed(evt[1]):
                print(evt)
                is_dir = 1 if (len(evt[1]) > 1 and evt[1][1] == 'IN_ISDIR') else 0
                action = 'delete' if evt[1][0] == 'IN_DELETE' else 'copy'
                ids = self.db.save((
                    evt[2],
                    evt[3],
                    is_dir,
                    action,
                    self.server,
                    0
                ))
                # send to server
                if True:
                    self.db.delete(ids)
                else:
                    pass  # TODO alert user

    def _is_temp_file(self, filename: str) -> bool:
        for f in self._temp_files:
            if f in filename:
                return True
        return False

    def _is_sync_needed(self, evt_types: list) -> bool:
        if evt_types[0] in self._synchronizable_events:
            return True
        return False
