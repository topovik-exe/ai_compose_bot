import aiogram
from aiogram.fsm.state import StatesGroup
from aiogram.fsm.state import State


class States(StatesGroup):
    none_state = State()
    waiting_for_password = State()
    waiting_for_scenario = State()
    waiting_for_avatar = State()
    waiting_for_prompt_midjourney = State()
    waiting_for_prompt_chatgpt = State()
    waiting_for_gpt_confirmation = State()
    confirm_audio = State()
    waiting_for_midjourney_confirmation = State()