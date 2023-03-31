from helpers import get_port, ainput, read, write
import asyncio

DEFAULT_HOST = '127.0.0.1'


def get_host():
    host = input(f'server host ({DEFAULT_HOST}): ')
    if not host:
        return DEFAULT_HOST
    else:
        return host


async def receive_loop(reader):
    while True:
        data = await read(reader)
        if data is None:
            return
        print(data.decode(), end='', flush=True)


async def send_loop(writer):
    while True:
        await write(writer, (await ainput()).encode())


async def main():
    host = get_host()
    port = get_port()
    reader, writer = await asyncio.open_connection(host, port)
    print(f'connected to {host}:{port}')
    await asyncio.wait(map(asyncio.create_task,
                           [receive_loop(reader), send_loop(writer)]),
                       return_when=asyncio.FIRST_COMPLETED)


if __name__ == '__main__':
    asyncio.run(main())
