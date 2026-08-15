from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_language = State()
    waiting_password = State()
    # Admin oldindan qo'shgan hodimlardan o'zini tanlash bosqichi
    waiting_link_choice = State()
    waiting_full_name = State()
    waiting_position = State()
    waiting_districts = State()
