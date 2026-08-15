from aiogram.fsm.state import State, StatesGroup


class SettingsStates(StatesGroup):
    editing_districts = State()
    editing_language = State()
