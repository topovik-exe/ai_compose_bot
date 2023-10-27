import asyncio
import logging
import sys

import markup
import tools
import os
import ai_interfaces

from dotenv import load_dotenv
from aiogram import Dispatcher, Bot
from aiogram import types
from aiogram.enums import ParseMode
from aiogram.filters import Command, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from multiprocessing import Process

from markup import choose_scenario, choose_avatar, generate_audio, confirm_gpt
from states import States


load_dotenv()
# Bot token can be obtained via https://t.me/BotFather
TOKEN = os.getenv('TOKEN')
password = os.getenv('PASSWORD')


# All handlers should be attached to the Router (or Dispatcher)
dp = Dispatcher(storage=MemoryStorage())
bot:Bot = None

class LoggedInFilter(BaseFilter):
    def __init__(self, flag:bool = True):
        self.flag = flag

    async def __call__(self, message:Message) -> bool:  # [3]
        global bot
        global dp
        state:FSMContext =  FSMContext(
            storage=dp.storage,
            key=StorageKey(
                chat_id=message.chat.id,
                user_id=message.from_user.id,
                bot_id=bot.id
            )
        )
        data = await state.get_data()
        if 'logged_in' in data:
            return data['logged_in'] == self.flag
        else:
            return not self.flag

class LockedFilter(BaseFilter):
    def __init__(self, flag:bool = True):
        self.flag = flag

    async def __call__(self, message:Message) -> bool:  # [3]
        global bot
        global dp
        state:FSMContext =  FSMContext(
            storage=dp.storage,
            key=StorageKey(
                chat_id=message.chat.id,
                user_id=message.from_user.id,
                bot_id=bot.id
            )
        )
        data = await state.get_data()
        if 'locked' in data:
            return data['locked']
        else:
            return False

@dp.message(LockedFilter())
async def locked_operation(message:Message):
    await message.answer('Дождитесь выполнения операции')

@dp.message(States.waiting_for_password)
async def check_password(message:Message, state:FSMContext):
    if not message.text or message.text != password:
        await message.answer(text='Введите корректный пароль.')
    else:
        await message.answer(text='Добро пожаловать.\n'
                                  'Для начала генерации видео введите команду /create.'
                                  'Если вы хотите вернуться к предыдущему шагу введите команду /step_back   \n')
        await state.update_data(logged_in=True)
        await state.set_state(States.none_state)

@dp.message(LoggedInFilter(False))
async def request_password(message: Message, state: FSMContext):
    await message.answer(text='Для доступа к боту введите пароль:')
    await state.set_state(States.waiting_for_password)

@dp.message(Command('step_back'))
async def step_back(message:Message, state:FSMContext):
    cur_state = await state.get_state()
    if cur_state == States.waiting_for_scenario \
            or cur_state == States.waiting_for_prompt_chatgpt\
            or cur_state == States.waiting_for_gpt_confirmation\
            or cur_state == States.waiting_for_avatar:
        await choose_scenario(message, state)
        await state.set_state(States.waiting_for_scenario)
        return
    if cur_state == States.waiting_for_midjourney_confirmation\
            or cur_state == States.waiting_for_prompt_midjourney:
        await choose_avatar(message, state)
        await state.set_state(States.waiting_for_avatar)


@dp.message(Command('create'))
async def create_options(message:Message, state:FSMContext):
    await choose_scenario(message, state)
    await state.set_state(States.waiting_for_scenario)

@dp.message(States.waiting_for_scenario)
async def scenario(message:Message, state:FSMContext):
    if not message.text:
        await message.answer('Введите корректные данные')
        return
    if message.text == 'Сгенерировать':
        await state.set_state(States.waiting_for_prompt_chatgpt)
        await message.answer(text='Теперь введите ваш запрос(prompt):',
                             reply_markup=types.ReplyKeyboardRemove())
    else:
        await state.set_state(States.waiting_for_avatar)
        await state.update_data(scenario=message.text)
        await choose_avatar(message, state)

@dp.message(States.waiting_for_prompt_chatgpt)
async def gpt_prompt(message:Message, state:FSMContext):
    if not message.text:
        await message.answer('Введите корректные данные')
        return
    await state.update_data(locked=True)
    await markup.confirm_gpt(message=message, state=state)

@dp.message(States.waiting_for_gpt_confirmation)
async def confirm_gpt(message:Message, state:FSMContext):
    if not message.text:
        await message.answer('Введите корректные данные')
    if message.text == 'Да':
        await choose_avatar(message, state)
        return
    if message.text == 'Нет':
        await state.set_state(States.waiting_for_prompt_chatgpt)
        await message.answer(text='Теперь введите ваш запрос(prompt):',
                             reply_markup=types.ReplyKeyboardRemove())
        return
    await message.answer('Введите корректные данные')

@dp.message(States.waiting_for_avatar)
async def avatar(message:Message, state:FSMContext):
    global bot
    if message.photo:
        path = await asyncio.wait_for(tools.disk_tools.download_photo_on_device(message=message,
                                                                                download_function=bot.download_file,
                                                                                get_file_function=bot.get_file),
                                timeout=100)
        await state.update_data(picture=path)
        await generate_audio(message, state)
        return

    if message.text == 'Сгенерировать':
        await state.set_state(States.waiting_for_prompt_midjourney)
        await message.answer(text='Теперь введите ваш запрос(prompt):',
                             reply_markup=types.ReplyKeyboardRemove())

@dp.message(States.waiting_for_prompt_midjourney)
async def midjourney_prompt(message:Message, state:FSMContext):
    if not message.text:
        await message.answer('Введите корректные данные')
        return
    await state.update_data(locked=True)
    await markup.confirm_midjourney(message=message, state=state)

@dp.message(States.waiting_for_midjourney_confirmation)
async def confirm_midjourney(message:Message, state:FSMContext):
    if not message.text:
        await message.answer('Введите корректные данные')
    if message.text == 'Да':
        await generate_audio(message, state)
        return
    if message.text == 'Нет':
        await state.set_state(States.waiting_for_prompt_midjourney)
        await message.answer(text='Теперь введите ваш запрос(prompt):',
                             reply_markup=types.ReplyKeyboardRemove())
        return
    await message.answer('Введите корректные данные')



async def main() -> None:
    global bot
    bot = Bot(TOKEN, parse_mode=ParseMode.HTML)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
