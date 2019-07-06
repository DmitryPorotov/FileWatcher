import ssh_client


cl = ssh_client.SshClient('dmitrydev.adquant.net', '/root/test')
cl.connect()