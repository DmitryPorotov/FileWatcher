import asyncio
import os
import stat
import inotify.adapters
from ssh_client import SshClient
from db_handler import DbHandler
import util
import sys
from pathlib import Path


class PathWatcher:
    _temp_files = ['___jb_old___', '___jb_tmp___', 'goutputstream-']
    _attrib_event = 'IN_ATTRIB'
    _copy_events = ['IN_CREATE', 'IN_MODIFY']
    _delete_event = 'IN_DELETE'
    _move_events = ['IN_MOVED_TO', 'IN_MOVED_FROM']
    _all_events = [_attrib_event, _delete_event, *_copy_events, *_move_events]

    def __init__(self, path_from, ssh_client, db):
        self.path_from = util.resolve_home_dir(path_from, is_dir=True)
        self.db = db  # type: DbHandler
        self._sftp = ssh_client  # type: SshClient
        self.evt_loop = asyncio.get_event_loop()
        self.cookie_to_future_map = {}
        try:
            asyncio.ensure_future(self._start_watcher())
            self.evt_loop.run_forever()
        except FileNotFoundError:
            print('Watch directory does not exist ' + self.path_from)
            exit(1)

    async def _start_watcher(self):
        i = inotify.adapters.InotifyTree(self.path_from)
        for evt in i.event_gen():
            if evt is not None and not self._is_temp_file(evt[3]) and PathWatcher._is_sync_needed(evt[1]):
                print(evt)
                is_dir = 1 if (len(evt[1]) > 1 and evt[1][1] == 'IN_ISDIR') else 0

                path = evt[2] if evt[2][-1] is '/' else evt[2] + '/'

                action = 'copy'
                if evt[1][0] == PathWatcher._delete_event:
                    action = 'delete'
                elif evt[1][0] == PathWatcher._attrib_event:
                    action = 'attrib'
                elif evt[1][0] == PathWatcher._move_events[0]:
                    action = 'move_to'
                elif evt[1][0] == PathWatcher._move_events[1]:
                    action = 'move_from'

                ids = self.db.save((
                    path,
                    evt[3],
                    is_dir,
                    action,
                    self._sftp.user + '@' + self._sftp.server,
                    0,
                    evt[0].cookie
                ))

                def cb():
                    self.db.delete(ids)

                if action in ['copy', 'delete', 'attrib']:
                    self._execute_transaction(action, path, evt[3], cb, is_dir)
                else:
                    self._try_defer(evt[0].cookie, cb)
            await asyncio.sleep(0)

    def _try_defer(self, cookie, cb):
        rows = self.db.get_by_cookie(cookie)
        future = self.evt_loop.create_future()
        self.cookie_to_future_map[str(cookie)] = future
        if len(rows) == 1:
            asyncio.ensure_future(self._defer(cookie, cb))
        elif len(rows) == 2:
            self._handle_move(rows)
            self._clean_up_future_by_cookie(cookie)
        else:
            pass  # TODO: handle db corruption

    async def _defer(self, cookie, cb):
        await asyncio.sleep(0.05)
        rows = self.db.get_by_cookie(cookie)
        if len(rows) == 1:
            self._execute_transaction('copy' if rows[0][5] == 'move_to' else 'delete', rows[0][2],
                                      rows[0][3], cb, bool(rows[0][4]))
        elif len(rows) == 2:
            self._handle_move(rows)
        self._clean_up_future_by_cookie(cookie)

    def _clean_up_future_by_cookie(self, cookie):
        if str(cookie) in self.cookie_to_future_map:
            self.cookie_to_future_map[str(cookie)].set_result(None)
            del self.cookie_to_future_map[str(cookie)]

    def _handle_move(self, rows):
        if rows[0][5] == 'move_to':
            row_to = rows[0]
            row_from = rows[1]
        else:
            row_to = rows[1]
            row_from = rows[0]
        self._execute_transaction('move', row_to[2], row_to[3],
                                  lambda: None, bool(rows[0][4]), row_from[2], row_from[3])
        self.db.delete(list(map(lambda r: r[0], rows)))

    def _execute_transaction(self, action, path, file_name, cb, is_dir, path_move_from='', file_name_move_from=''):
        try:
            rel_full_path = self._get_relative_path(path) + file_name
            if action == 'copy':
                if not is_dir:
                    if Path(path + file_name).is_symlink():
                        original = os.readlink(path + file_name)
                        self._sftp.symlink(self._get_relative_path(path), original, cb)
                    else:
                        self._sftp.put(rel_full_path, cb)
                else:
                    mask = stat.S_IMODE(os.stat(rel_full_path).st_mode)
                    self._sftp.mkdir(rel_full_path, mask, cb)
            elif action == 'delete':
                if not is_dir:
                    self._sftp.remove(rel_full_path, cb)
                else:
                    self._sftp.rmdir(rel_full_path, cb)
            elif action == 'move':
                self._sftp.move(self._get_relative_path(path_move_from) + file_name_move_from, rel_full_path)
            elif action == 'attrib':
                pass

        except:
            e = sys.exc_info()[0]
            print(e)
            raise e
            pass
            # TODO: give user a warning

    def _is_temp_file(self, filename: str) -> bool:
        for f in self._temp_files:
            if f in filename:
                return True
        return False

    @staticmethod
    def _is_sync_needed(evt_types: list) -> bool:
        if evt_types[0] in PathWatcher._all_events:
            return True
        return False

    def _get_relative_path(self, path):
        return path.split(self.path_from)[1]
