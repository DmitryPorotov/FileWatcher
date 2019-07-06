from paramiko import transport, RSAKey, SFTPClient, client
import socket
import util


class SshClient:
    def __init__(self, server: str, path_to: str, path_from: str, key_file: str = '~/.ssh/id_rsa'):
        self._sftp_client = None  # type: SFTPClient
        parts = server.split("@")
        self.server = parts[1]
        self.user = parts[0]

        self._path_to = util.resolve_home_dir(path_to, is_dir=True)
        self._path_from = util.resolve_home_dir(path_from, is_dir=True)
        self._p_key = RSAKey.from_private_key_file(util.resolve_home_dir(key_file))
        self.key_file_name = key_file
        self._connect()

    def _connect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.server, 22))
        tr = transport.Transport(s)
        tr.connect(username=self.user, pkey=self._p_key)
        self._sftp_client = tr.open_sftp_client()

    def put(self, rel_file_name, callback=None):
        def cb(cur, total):
            if cur == total and callback:
                callback()
        self._sftp_client.put(self._path_from + rel_file_name, self._path_to + rel_file_name, cb)

    def mkdir(self, rel_dir_name, mask, callback):
        self._sftp_client.mkdir(self._path_to + rel_dir_name, mask)
        callback()

    def remove(self, rel_file_name, callback):
        self._sftp_client.remove(self._path_to + rel_file_name)
        callback()

    def rmdir(self, rel_dir_name, callback):
        self._sftp_client.remove(self._path_to + rel_dir_name)
        callback()

    def move(self, rel_dir_name_from, rel_file_name):
        self._sftp_client.rename(self._path_to + rel_dir_name_from, self._path_to + rel_file_name)

    def symlink(self, destination_dir_name, original, callback):
        cl = client.SSHClient()
        cl.load_system_host_keys()
        cl.connect(self.server, username=self.user)
        stdin, stdout, stderr = cl.exec_command('ln -s {} {}'.format(original,
                                                                     self._path_to + destination_dir_name))
        callback()

    def close(self):
        self._sftp_client.close()
