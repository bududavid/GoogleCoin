from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from DATA import currencies


# Клавиатуры
button_earn = KeyboardButton(text='💰 Заработать')
button_accounts = KeyboardButton(text='📜 Аккаунты')
button_balance = KeyboardButton(text='💵 Баланс')
button_withdraw = KeyboardButton(text='💸 Вывести')
button_currency = KeyboardButton(text='🌐 Выбор валюты')
button_help = KeyboardButton(text='❓ Помощь/Жалобы')
button_referrals = KeyboardButton(text='👥 Рефералы')

# Создание клавиатуры с двумя колонками
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [button_earn, button_accounts],
        [button_balance, button_withdraw],
        [button_currency, button_help],
        [button_referrals]
    ],
    resize_keyboard=True
)


button_payeer = KeyboardButton(text='🅿️ Payeer')
button_cards = KeyboardButton(text='В будущем здесь появится возможность вывести на MAIB и ViktoriaBank')
button_back = KeyboardButton(text='🔙 Назад')
withdraw_keyboard = ReplyKeyboardMarkup(keyboard=[[button_payeer], [button_cards], [button_back]], resize_keyboard=True)

maib = KeyboardButton(text='MAIB')
vicbn = KeyboardButton(text='Victoriabank')
button_back2 = KeyboardButton(text='Назад')

cards_keyboard = ReplyKeyboardMarkup(keyboard=[[maib], [vicbn], [button_back2]],  resize_keyboard=True)

currency_buttons = [[KeyboardButton(text=currency)] for currency in currencies]
# Вставка кнопки "Назад" в начало списка
currency_buttons.insert(0, [button_back])
# Создание клавиатуры с настройкой размера кнопок
currency_keyboard = ReplyKeyboardMarkup(keyboard=currency_buttons, resize_keyboard=True)


help_button = KeyboardButton(text='❓ Часто задаваемые вопросы')
write_andmin = KeyboardButton(text='✉️ Написать в поддержку')

help_keyboard = ReplyKeyboardMarkup(keyboard=[[help_button, write_andmin], [button_back]], resize_keyboard=True)