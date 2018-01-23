import time

import paramiko


class SomeSSHThing(object):
    def __init__(self, ip, username, password):
        self._ip = ip
        self._username = username
        self._password = password

        self._connection = paramiko.SSHClient()
        self._connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self._channel = None

    def connect(self):
        self._connection.connect(
            hostname=self._ip,
            username=self._username,
            password=self._password,
        )

        self._channel = self._connection.invoke_shell()

    def send(self, data):
        self._channel.send(data)

    def recv(self, length=16348):
        return self._channel.recv(length)

    def read_until(self, delimiter):
        data = ''
        while delimiter not in data:
            data += self.recv(1)

        return data

    def disconnect(self):
        self._channel.close()
        self._connection.close()


if __name__ == '__main__':
    s = SomeSSHThing(
        ip='192.168.137.253',
        username='user',
        password='password',
    )

    s.connect()

    s.read_until('$')

    s.send('ifconfig\r\n')

    print
    s.read_until('$')

    s.disconnect()



import paramiko
k = paramiko.RSAKey.from_private_key_file("/Users/whatever/Downloads/mykey.pem")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print "connecting"
c.connect( hostname = "www.acme.com", username = "ubuntu", pkey = k )
print "connected"
commands = [ "/home/ubuntu/firstscript.sh", "/home/ubuntu/secondscript.sh" ]
for command in commands:
    print "Executing {}".format( command )
    stdin , stdout, stderr = c.exec_command(command)
    print stdout.read()
    print( "Errors")
    print stderr.read()
c.close()import paramiko
k = paramiko.RSAKey.from_private_key_file("/Users/whatever/Downloads/mykey.pem")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print "connecting"
c.connect( hostname = "www.acme.com", username = "ubuntu", pkey = k )
print "connected"
commands = [ "/home/ubuntu/firstscript.sh", "/home/ubuntu/secondscript.sh" ]
for command in commands:
    print "Executing {}".format( command )
    stdin , stdout, stderr = c.exec_command(command)
    print stdout.read()
    print( "Errors")
    print stderr.read()
c.close()