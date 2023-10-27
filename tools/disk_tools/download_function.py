import asyncio

import aiogram
counter = 0

async def download_photo_on_device(message:aiogram.types.Message, download_function:callable, get_file_function:callable):
    global counter
    counter = counter + 1
    await asyncio.wait_for(
        download_function((await get_file_function(message.photo[-1].file_id)).file_path, f'data\{str(counter)}.jpg'),
        timeout=100
    )
    return f'data\{str(counter)}.jpg'

