from aiogram.fsm.state import State, StatesGroup


class AdminEmployeeStates(StatesGroup):
    entering_name = State()
    entering_position = State()
    choosing_districts = State()
    confirming = State()
    editing_select = State()
    editing_name = State()
    editing_position = State()
    editing_districts = State()
    editing_confirm = State()


class AdminPasswordStates(StatesGroup):
    entering_current = State()
    entering_new = State()
    entering_confirm = State()


class AdminRoleStates(StatesGroup):
    choosing_employee = State()
    choosing_role = State()
    confirming = State()


class AdminReportStates(StatesGroup):
    entering_date = State()
    choosing_employee = State()


class AdminExportStates(StatesGroup):
    entering_range = State()
