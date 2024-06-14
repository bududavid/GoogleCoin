from aiogram.fsm.state import State, StatesGroup

class WithdrawState(StatesGroup):
    awaiting_withdraw_amount = State()
    awaiting_wallet_number = State()

class HelpComplaintState(StatesGroup):
    awaiting_message = State()
    awaiting_response = State()
    awaiting_image = State()

class AdminReplyState(StatesGroup):
    awaiting_reply = State()

class CheckAccountStates(StatesGroup):
    confirm_creation = State()
    confirm_phone_removal = State()
    confirm_backup_email_removal = State()
    complete_check = State()

class NameSurname(StatesGroup):
    waiting_for_name = State()
    waiting_for_card_number = State()