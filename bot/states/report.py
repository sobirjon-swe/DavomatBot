from aiogram.fsm.state import State, StatesGroup


class ReportStates(StatesGroup):
    choosing_type = State()
    choosing_subtype = State()
    choosing_partners = State()
    choosing_district = State()
    entering_customer = State()
    sending_location = State()
    sending_photos = State()
    entering_plots = State()
    confirming = State()
