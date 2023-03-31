import asyncio
import sys

DEFAULT_PORT = 9090


def get_port() -> int:
    port = input(f'server port ({DEFAULT_PORT}): ')
    if not port:
        return DEFAULT_PORT
    else:
        return int(port)


async def ainput(msg: str = None) -> str:
    if msg is not None:
        print(msg, end='', flush=True)
    return (await asyncio.get_event_loop().run_in_executor(
        None, sys.stdin.readline))[:-1]


async def read(reader: asyncio.StreamReader, n: int = 1024) -> bytes:
    data = await reader.read(n)
    if not data:
        return None
    return data[4:]


async def write(writer: asyncio.StreamWriter, data: bytes):
    writer.write('{:04}'.format(len(data)).encode() + data)
    await writer.drain()
