from helpers import get_port, ainput, read, write
import errno
import shelve
from hashlib import pbkdf2_hmac
import secrets
from base64 import b64encode
import asyncio
from asyncio import Event


class Server:
    def __init__(self):
        self.authorized_writers = set()
        self.passwords_db = shelve.open('passwords')
        self.session_tokens_db = shelve.open('session_tokens')

        self.pause_event = Event()
        self.pause_event.set()

    def log(self, *values):
        with open('server.log', 'a') as f:
            print(*values, file=f)

    async def run(self):
        try:
            self.serv = await asyncio.start_server(self.handle_connection,
                                                   port=get_port())
        except OSError as e:
            if e.errno == errno.EADDRINUSE:
                print('port is not available, using a free port')
                self.serv = await asyncio.start_server(self.handle_connection)
            else:
                raise e

        print(
            f'server started at port {self.serv.sockets[0].getsockname()[1]}')

        await asyncio.wait(map(asyncio.create_task,
                               [self.serv.serve_forever(), self.input_loop()]),
                           return_when=asyncio.FIRST_COMPLETED)

    async def authenticate(self, reader, writer) -> bool:
        def greet(name):
            return b'hello ' + name.encode() + b'\n'

        await write(writer, b'session token (blank if none): ')
        session_token = await read(reader)
        if session_token:
            session_token = session_token.decode()
            for st, n in self.session_tokens_db.items():
                if session_token == st:
                    name = n
                    self.log('authenticated using session token')
                    await write(writer, greet(name))
                    return name
            await write(writer, b'wrong session token!\n')
            self.log('got wrong session token')
        else:
            await write(writer, b'username: ')
            name = (await read(reader)).decode()
            await write(writer, b'password: ')
            password = await read(reader)
            salt_and_hash = self.passwords_db.get(name)
            if salt_and_hash is None:
                salt = secrets.token_bytes(512 // 8)
                hash = pbkdf2_hmac('sha256', password, salt, 100_000)
                self.passwords_db[name] = (salt, hash)
                session_token = b64encode(secrets.token_bytes())
                self.session_tokens_db[session_token.decode()] = name
                self.log('registered user')
                await write(writer, greet(name) + b'your session token is '
                            + session_token + b'\n')
                return name
            else:
                (salt, hash) = salt_and_hash
                if pbkdf2_hmac('sha256', password, salt, 100_000) == hash:
                    self.log('authenticated using password')
                    session_token = b64encode(secrets.token_bytes())
                    self.session_tokens_db[session_token.decode()] = name
                    await write(writer, greet(name)
                                + b'your new session token is '
                                + session_token + b'\n')
                    return name
                else:
                    await write(writer, b'wrong password!\n')
                    self.log('got wrong password')

    async def handle_connection(self, reader, writer):
        name = await self.authenticate(reader, writer)
        if not name:
            return

        self.authorized_writers.add(writer)

        while True:
            await self.pause_event.wait()
            try:
                msg = await asyncio.wait_for(read(reader), timeout=1)
            except asyncio.TimeoutError:
                continue
            if msg is None:
                self.log('user disconnected')
                self.authorized_writers.remove(writer)
                break
            self.log(f'received {len(msg)} bytes')

            for user in self.authorized_writers:
                if user is not writer:
                    await write(user, name.encode() + b': ' + msg + b'\n')

    async def input_loop(self):
        while True:
            command = await ainput('> ')
            if command == 'exit':
                return
            elif command == 'pause':
                self.pause_event.clear()
            elif command == 'unpause':
                self.pause_event.set()
            elif command == 'show-logs':
                with open('server.log') as f:
                    print(f.read())
            elif command == 'clear-logs':
                open('server.log', 'w').close()
            elif command == 'clear-credentials':
                self.passwords_db.clear()
                self.session_tokens_db.clear()
            else:
                print('unknown command')


async def main():
    await Server().run()


if __name__ == '__main__':
    asyncio.run(main())
