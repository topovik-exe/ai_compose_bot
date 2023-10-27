import time
import asyncio

import aiogram
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, KeyboardButton, FSInputFile, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

import ai_interfaces.open_ai
from states import States

async def new_loop(func):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(func)
    loop.close()



def generate_button_markup():
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='Сгенерировать')]],
        resize_keyboard=True
    )
    return kb

def yes_no_markup():
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='Да'), KeyboardButton(text='Нет')]],
        resize_keyboard=True
    )
    return kb


async def choose_scenario(message:Message, state:FSMContext):
    await message.answer(text='Вы попали в мастер создания.\n'
                              'Для начала введите сценарий(текст) вашего видео.\n'
                              'Либо же нажмите на кнопку "сгенерировать" чтобы текст сгенерировала нейронная сеть.\n',
                         reply_markup=generate_button_markup())
async def choose_avatar(message:Message, state:FSMContext):
    await state.set_state(States.waiting_for_avatar)
    await message.answer(
        text='Теперь пришлите желаемый аватар(вы можете нажать на кнопку сгенерировать для создания аватара):',
        reply_markup=generate_button_markup())

async def generate_audio(message:Message, state:FSMContext):
    await state.update_data(locked=True)
    data = await state.get_data()
    text = data['scenario']
    image = FSInputFile(data['picture'])
    await message.answer(text='Хахахахахха, попался негр',
                         reply_markup=types.ReplyKeyboardRemove())
    await message.answer(text=f'Твой сценарий:\n'
                              f'{text}')
    await asyncio.wait_for(
        message.answer_photo(caption=f'А это твой аватар:',
                             photo=image),
        timeout=100)
    await state.update_data(locked = False)

async def confirm_gpt(message:Message, state:FSMContext):
    await state.update_data(locked=True)
    text = await asyncio.wait_for(ai_interfaces.open_ai.generate_text_by_prompt(text=message.text),
                                  timeout=100)
    await message.answer(text=f'Сценарий для видео:\n'
                              f'{text}\n'
                              f'Вас устраивает текущий текст?\n'
                              f'В случае нажатия на кнопку Нет запустится новая генерация текста.',
                         reply_markup=yes_no_markup())
    await state.set_state(States.waiting_for_gpt_confirmation)
    await state.update_data(scenario=text, locked=False)

async def confirm_midjourney(message:Message, state:FSMContext):
    await state.update_data(locked=True)
    path = await asyncio.wait_for(ai_interfaces.midjourney.generate_image_by_prompt(text=message.text),
                                  timeout=100)
    await asyncio.sleep(10)
    file = FSInputFile(path=path)
    await message.answer(text=f'Аватар для видео:\n')
    await message.answer_photo(photo=file)
    await message.answer(text='Вас устраивает текущий аватар?\n'
                              f'В случае нажатия на кнопку Нет запустится новая генерация аватара.',
                         reply_markup=yes_no_markup())
    await state.set_state(States.waiting_for_midjourney_confirmation)
    await state.update_data(picture=path, locked=False)
