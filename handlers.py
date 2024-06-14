import logging
import random
import sqlite3
import re
import aiohttp
import math
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ContentType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from unidecode import unidecode
from DATA import (
    french_first_names, french_last_names, russian_first_names,
    russian_last_names, english_first_names, english_last_names,
    API_TOKEN, CHECK_CHAT_ID, CHECK_CHAT_ID_HELP, MIN_FOR_CONCLUSION, ACCRUAL, currencies,
    REFERRAL_BONUS, WITHDRAWAL_PERCENTAGE, DAY_HOLD
)
from keyboards import keyboard, withdraw_keyboard, withdraw_keyboard, currency_keyboard, help_keyboard
from states import (
    WithdrawState, HelpComplaintState, AdminReplyState, CheckAccountStates, NameSurname
) 
from database import cursor, conn, cursor2, conn2


logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


async def get_exchange_rate(from_currency, to_currency):
    url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return data['rates'].get(to_currency, 1)

def is_valid_payeer_wallet(wallet):
    return re.match(r'^P[0-9]{3,16}$', wallet) is not None


def register_handlers(dp: Dispatcher):
    dp.message.register(send_welcome, Command("start"))
    dp.message.register(help_complaint, F.text == '❓ Помощь/Жалобы')
    dp.message.register(help_quesions, F.text == '❓ Часто задаваемые вопросы')
    dp.message.register(help_write, F.text == '✍ Написать в поддержку')
    dp.message.register(send_credentials, F.text == '💰 Заработать')
    dp.message.register(referral_link, F.text == '👥 Рефералы')
    dp.message.register(show_accounts, F.text == '📜 Аккаунты')
    dp.message.register(show_balance, F.text == '💵 Баланс')
    dp.message.register(select_currency, F.text == '🌐 Выбор валюты')
    dp.message.register(set_currency, lambda message: message.text in currencies)
    dp.message.register(withdraw_request, F.text == '💸 Вывести')
    dp.message.register(back_to_main_menu, F.text == '🔙 Назад')
    dp.message.register(select_payeer, F.text == '🅿️ Payeer')
    dp.message.register(process_withdraw_amount, WithdrawState.awaiting_withdraw_amount)
    dp.message.register(process_wallet_number, WithdrawState.awaiting_wallet_number)
    dp.message.register(send_admin_reply, AdminReplyState.awaiting_reply)
    dp.message.register(help_complaint, Command(commands=['help_complaint']))
    dp.message.register(receive_help_complaint, HelpComplaintState.awaiting_message)
    dp.message.register(receive_image, HelpComplaintState.awaiting_image)
    dp.message.register(skip_image, Command("skip"))
    dp.message.register(ask_admin_for_reply, lambda c: c.data and c.data.startswith('reply|'))

    dp.callback_query.register(process_check, lambda c: c.data and c.data.startswith('check'))
    dp.callback_query.register(process_result, lambda c: c.data and c.data.startswith('result'))
    dp.callback_query.register(process_withdraw_done, lambda c: c.data and c.data.startswith('withdraw_done'))
    dp.callback_query.register(process_withdraw_failed, lambda c: c.data and c.data.startswith('withdraw_failed'))
    dp.callback_query.register(process_confirm_creation, lambda c: c.data in ["confirm_creation_yes", "confirm_creation_no"])
    dp.callback_query.register(process_confirm_phone_removal, lambda c: c.data in ["confirm_phone_removal_yes", "confirm_phone_removal_no"])
    dp.callback_query.register(process_confirm_backup_email_removal, lambda c: c.data in ["confirm_backup_email_removal_yes", "confirm_backup_email_removal_no"])
    dp.callback_query.register(process_reply, lambda c: c.data and c.data.startswith('reply'))
    dp.callback_query.register(process_cancel_registration, lambda c: c.data and c.data.startswith('cancel|'))

    



@dp.callback_query(lambda c: c.data and c.data.startswith('check'))
async def process_check(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        data = callback_query.data.split('|')
        temp_id = int(data[1])

        # Сохраняем temp_id в состояние
        await state.update_data(temp_id=temp_id)
        
        # Переходим к первому вопросу
        await callback_query.message.answer("Вы точно создали аккаунт?", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="confirm_creation_yes"), InlineKeyboardButton(text="Нет", callback_data="confirm_creation_no")]
        ]))
        await state.set_state(CheckAccountStates.confirm_creation)
    except Exception as e:
        logging.error(f"Ошибка при проверке учётных данных: {e}")
        await callback_query.message.answer(f"Ошибка отправки сообщения: {e}")

@dp.callback_query(lambda c: c.data in ["confirm_creation_yes", "confirm_creation_no"])
async def process_confirm_creation(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "confirm_creation_yes":
        await callback_query.message.answer("Вы точно удалили номер телефона? Если нет удалите, иначе ваш аккаунт не будет принят", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="confirm_phone_removal_yes"), InlineKeyboardButton(text="Нет", callback_data="confirm_phone_removal_no")]
        ]))
        await state.set_state(CheckAccountStates.confirm_phone_removal)
    else:
        await callback_query.message.answer("Пожалуйста, создай аккаунт и попробуй снова.")
        for i in range(1):
            await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id - i)
        await state.clear()

@dp.callback_query(lambda c: c.data in ["confirm_phone_removal_yes", "confirm_phone_removal_no"])
async def process_confirm_phone_removal(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "confirm_phone_removal_yes":
        await callback_query.message.answer("Вы точно удалили резервную почту? Если нет удалите, иначе ваш аккаунт не будет принят", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="confirm_backup_email_removal_yes"), InlineKeyboardButton(text="Нет", callback_data="confirm_backup_email_removal_no")]
        ]))
        await state.set_state(CheckAccountStates.confirm_backup_email_removal)
    else:
        await callback_query.message.answer("Пожалуйста, удали номер телефона и попробуй снова.")
        for i in range(2):
            await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id - i)
        await state.clear()

@dp.callback_query(lambda c: c.data in ["confirm_backup_email_removal_yes", "confirm_backup_email_removal_no"])
async def process_confirm_backup_email_removal(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "confirm_backup_email_removal_yes":
        # Завершаем процесс проверки
        data = await state.get_data()
        temp_id = data.get('temp_id')
        
        # Отправка на проверку
        cursor.execute('SELECT login, password FROM temp_check WHERE id = ?', (temp_id,))
        temp_data = cursor.fetchone()
        try:
            for i in range(4):
                await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id - i)
        except Exception as e:
            logging.error(f"Ошибка при удалении сообщения: {e}")
            await callback_query.answer("Ошибка при удалении сообщения.")
        
        if temp_data:
            login, password = temp_data 
            user = await bot.get_chat(callback_query.from_user.id)
            inline_kb_check = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Рабочий", callback_data=f"result|{temp_id}|working"), 
                 InlineKeyboardButton(text="Не рабочий", callback_data=f"result|{temp_id}|not_working")]
            ])
            
            # Зачисляем средства на hold баланс
            cursor.execute('INSERT OR IGNORE INTO balances (user_id, balance, hold_balance) VALUES (?, 0, 0)', (callback_query.from_user.id,))
            cursor.execute(f'UPDATE balances SET hold_balance = hold_balance + {ACCRUAL} WHERE user_id = ?', (callback_query.from_user.id,))
            conn.commit()

            print(f"{user.full_name} - Создал аккаунт")
            
            await callback_query.answer()
            await bot.send_message(CHECK_CHAT_ID, f"Проверка логина и пароля:\nЛогин: {login}\nПароль: {password}", reply_markup=inline_kb_check)
            await callback_query.message.answer(
                f"📩 Сообщение с логином и паролем отправлено для проверки.\n\n"
                f"💵 На данный момент на ваш холд-баланс было зачислено: {ACCRUAL}$.\n"
                f"⏳ Аккаунт будет находиться в холде: {DAY_HOLD} дней, после чего на ваш баланс будет зачислено: {ACCRUAL}$.\n\n"
                f"🙏 Спасибо за понимание!"
            )
        else:
            await callback_query.message.answer("Ошибка: временные данные не найдены.")
        
        await state.clear()
    else:
        await callback_query.message.answer("Пожалуйста, удали резервную почту и попробуй снова.")
        for i in range(3):
            await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id - i)
        await state.clear()

@dp.callback_query(lambda c: c.data and c.data.startswith('reply'))
async def process_reply(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        data = callback_query.data.split('|')
        user_id = int(data[1])

        # Сохранение user_id в состоянии администратора
        await state.update_data(reply_to_user_id=user_id)

        await callback_query.message.answer(f"Введите ответ для пользователя {user_id}:")
        await state.set_state(AdminReplyState.awaiting_reply)
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Ошибка при обработке ответа: {e}")
        await callback_query.message.answer("Произошла ошибка при обработке ответа. Попробуйте позже.")

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    cursor2.execute("PRAGMA table_info(accounts);")
    columns = cursor.fetchall()
    print(columns)
    cursor.execute("ALTER TABLE accounts ADD COLUMN is_channel TEXT;")
    conn.commit()
    cursor2.execute("PRAGMA table_info(accounts);")
    columns = cursor.fetchall()
    print(columns)
    conn2.commit()
    # Для паши!!!
    # cursor = conn.cursor()
    # for user_id in range(1, 113):
    #     cursor.execute('''
    #     INSERT INTO referrals (user_id, referrer_id, earnings)
    #     VALUES (?, ?, ?)
    #     ''', (user_id, 1022037499, 0.01))

    # # Сохранение изменений и закрытие подключения
    # conn.commit()
    # conn.close()

    referrer_id = None
    if len(message.text.split()) > 1:

        referrer_id = int(message.text.split()[1])
        print(referrer_id)

    print(referrer_id)
    cursor.execute('INSERT OR IGNORE INTO users (user_id, score, created_accounts) VALUES (?, 0, 0)', (message.from_user.id,))

    if referrer_id != message.from_user.id:
        cursor.execute('INSERT OR IGNORE INTO referrals (user_id, referrer_id, earnings) VALUES (?, ?, 0.0)', (message.from_user.id, referrer_id))
        cursor.execute('UPDATE referrals SET earnings = earnings + ? WHERE user_id = ? AND referrer_id = ?', (REFERRAL_BONUS, message.from_user.id, referrer_id))
        cursor.execute('INSERT OR IGNORE INTO balances (user_id, balance) VALUES (?, 0.0)', (referrer_id,))
        cursor.execute('UPDATE balances SET balance = balance + ? WHERE user_id = ?', (REFERRAL_BONUS, referrer_id))
    
    conn.commit()

    await message.answer(
        f'👋 Привет, друг! Добро пожаловать в финансовое приключение! \n\n 💰Регистрируйте аккаунты Gmail и получайте за это оплату. За каждый аккаунт вы получите: {ACCRUAL}$\n\n 🤩Все очень просто. Бот выдает вам данные для регистрации Gmail аккаунта, вы копируете их и направляетесь в Google. Создаете там аккаунт Gmail, после чего возвращаетесь в бота. \n\n📧Основная валюта в боте USD - Американский доллар, однако вы можете выбрать одну из {len(currencies)} валют, которая будет использоваться для визуального отображения. 💵\n\n❗Выбранная вами валюта влияет только на визуальное отображение, её всегда можно сменить в любой момент.\n\n❓Если у вас возникнут проблемы или вопросы, просто нажмите на кнопку «❓ Помощь/Жалобы» и напишите, что случилось.', 
        reply_markup=keyboard
    )

@dp.message(F.text == '❓ Помощь/Жалобы')
async def help_complaint(message: types.Message):
    await message.answer("Вы можете написать в поддержку 📧 или узнать ответ на часто задаваемый вопрос ❓", reply_markup=help_keyboard)

@dp.message(F.text == '❓ Часто задаваемые вопросы')
async def help_quesions(message: types.Message):
    await message.answer(
        '🕐 Что такое холд?\n\n'
        '"Холд" - это 5-дневный период, в течение которого "отлеживается" аккаунт Gmail. Дело в том, что в течение 5 дней после создания аккаунта, Google может его заблокировать. По истечении "отлежки", аккаунт попадает на модерацию, после которой происходит начисление средств на "Баланс".\n\n'
        '♾ Сколько аккаунтов может принять бот?\n\n'
        'Бот примет любое количество аккаунтов, которое вы сможете зарегистрировать. Главное, чтобы Google не заблокировал их в период 5-дневного холда.\n\n'
        '👤 Как работает реферальная система?\n\n'
        'Каждый пользователь, который перейдет в бота по вашей реферальной ссылке, станет вашим рефералом.\n\n'
        'Каждый Gmail аккаунт, зарегистрированный вашим рефералом, принесет вам на баланс реферальное отчисление, но только после того, как Gmail аккаунт вашего реферала будет принят.\n\n'
        'Вы можете иметь любое количество рефералов.',
        reply_markup=help_keyboard
    )

@dp.message(F.text == '✉️ Написать в поддержку')
async def help_write(message: types.Message, state: FSMContext):
    await state.set_state(HelpComplaintState.awaiting_message)
    await message.answer("Пожалуйста, напишите ваше сообщение, и оно будет отправлено администратору.")

@dp.message(HelpComplaintState.awaiting_message, F.content_type == 'text')
async def receive_help_complaint(message: types.Message, state: FSMContext):
    await state.update_data(user_message=message.text, user_id=message.from_user.id)
    await state.set_state(HelpComplaintState.awaiting_image)
    await message.answer("Пожалуйста, отправьте изображение, если оно необходимо. Если изображение не нужно, нажмите /skip.")

@dp.message(HelpComplaintState.awaiting_image, F.content_type == 'photo')
async def receive_image(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_message = data.get('user_message')
    user_id = data.get('user_id')
    admin_chat_id = CHECK_CHAT_ID_HELP

    photo = message.photo[-1]
    photo_file_id = photo.file_id

    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ответить", callback_data=f"reply|{user_id}")]
    ])

    await bot.send_photo(admin_chat_id, photo_file_id, caption=f"Сообщение от пользователя {user_id}: {user_message}", reply_markup=inline_kb)
    await message.answer("Ваше сообщение с изображением отправлено администратору. Ожидайте ответа.")
    await state.clear()

@dp.message(HelpComplaintState.awaiting_image, F.content_type == 'text', F.text.lower() == '/skip')
async def skip_image(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_message = data.get('user_message')
    user_id = data.get('user_id')
    admin_chat_id = CHECK_CHAT_ID_HELP

    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ответить", callback_data=f"reply|{user_id}")]
    ])

    await bot.send_message(admin_chat_id, f"Сообщение от пользователя {user_id}: {user_message}", reply_markup=inline_kb)
    await message.answer("Ваше сообщение отправлено администратору. Ожидайте ответа.")
    await state.clear()

@dp.callback_query(lambda c: c.data and c.data.startswith('reply|'))
async def ask_admin_for_reply(callback_query: types.CallbackQuery, state: FSMContext):
    _, user_id = callback_query.data.split('|')
    user_id = int(user_id)

    await state.update_data(reply_to_user_id=user_id)
    await state.set_state(AdminReplyState.awaiting_reply)
    await callback_query.message.answer("Пожалуйста, введите ваш ответ для пользователя.")
    await callback_query.answer()

@dp.message(AdminReplyState.awaiting_reply)
async def send_admin_reply(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        user_id = data.get('reply_to_user_id')
        admin_reply = message.text

        await bot.send_message(user_id, f"Ответ от администратора: {admin_reply}")
        await message.answer("Ответ отправлен пользователю.")
        await state.clear()
    except Exception as e:
        logging.error(f"Ошибка при отправке ответа пользователю: {e}")
        await message.answer("Произошла ошибка при отправке ответа пользователю. Попробуйте позже.")

@dp.message(F.text == '💰 Заработать')
async def send_credentials(message: types.Message):
    try:
        first_names = french_first_names + english_first_names + russian_first_names
        last_names = french_last_names + english_last_names + russian_last_names
        

        your_first_name = random.choice(first_names)
        your_last_name = random.choice(last_names)

        random_number = random.randint(1000, 9999)

        your_first_name_normalized = unidecode(your_first_name).lower()
        your_last_name_normalized = unidecode(your_last_name).lower()

        your_username = f"{your_first_name_normalized}.{your_last_name_normalized}{random_number}"

        login = your_username

        def generate_random_password(length=12):
            chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!@#$%^&*()"
            password = ''.join(random.choice(chars) for _ in range(length))
            return password

        password = generate_random_password()

        # Сохраняем данные в временную таблицу
        cursor.execute('INSERT INTO temp_check (user_id, login, password) VALUES (?, ?, ?)', (message.from_user.id, login, password))
        temp_id = cursor.lastrowid
        conn.commit()

        # Создаем Inline клавиатуру с кнопками "Готово" и "Отменить регистрацию"
        inline_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Готово", callback_data=f"check|{temp_id}"), 
             InlineKeyboardButton(text="❌ Отменить регистрацию", callback_data=f"cancel|{temp_id}")]
        ])

        await message.answer(f"🆔 Логин: `{login}`@gmail.com\n🔑 Пароль: `{password}`\nЗа правильно созданный аккаунт вы получите {ACCRUAL}$", reply_markup=inline_kb, parse_mode="MARKDOWN")
    except Exception as e:
        logging.error(f"Ошибка при генерации учётных данных: {e}")
        await message.answer("⚠️ Произошла ошибка при генерации учётных данных. Попробуйте позже.")

@dp.callback_query(lambda c: c.data and c.data.startswith('cancel|'))
async def process_cancel_registration(callback_query: types.CallbackQuery):
    _, temp_id = callback_query.data.split('|')
    temp_id = int(temp_id)

    # Удаление записи из временной таблицы
    cursor.execute('DELETE FROM temp_check WHERE id = ?', (temp_id,))
    conn.commit()

    await callback_query.message.delete()
    await callback_query.message.answer("Регистрация аккаунта была отменена. Вы можете попробовать снова.")
    await callback_query.answer()

@dp.message(F.text == '👥 Рефералы')
async def referral_link(message: types.Message):
    user_id = message.from_user.id
    referral_code = f"{user_id}"
    referral_url = f"https://t.me/GoogleCoinUpbot?start={referral_code}"
    
    # Fetch the number of referrals and earnings from the database
    cursor.execute("SELECT COUNT(*), SUM(earnings) FROM referrals WHERE referrer_id=?", (user_id,))
    referrals_count, total_earnings = cursor.fetchone()
    total_earnings = total_earnings or 0  # Handle None case

    response_message = (
        f"👥 <b>Ваша реферальная ссылка</b>\n"
        f"<code>{referral_url}</code>\n\n"
        f"📊 <b>Количество рефералов:</b> {referrals_count}\n"
        f"💵 <b>Заработано на рефералах:</b> ${total_earnings:.2f}\n\n"
        f"🔹 <b>Платится за каждого реферала:</b> ${REFERRAL_BONUS:.2f}\n"
        # f"🔹 <b>Процент с вывода каждого реферала:</b> {WITHDRAWAL_PERCENTAGE * 100}%\n"
    )

    await message.answer(response_message, parse_mode='HTML')

@dp.message(F.text == '📜 Аккаунты')
async def show_accounts(message: types.Message):
    try:
        cursor.execute('SELECT created_accounts FROM users WHERE user_id = ?', (message.from_user.id,))
        user_data = cursor.fetchone()

        if user_data:
            await message.answer(f"Всего созданных аккаунтов: {user_data[0]}")
        else:
            await message.answer("У вас пока нет созданных аккаунтов.")
    except Exception as e:
        logging.error(f"Ошибка при отображении аккаунтов: {e}")
        await message.answer("Произошла ошибка при отображении аккаунтов. Попробуйте позже.")

@dp.message(F.text == '💵 Баланс')
async def show_balance(message: types.Message):
    try:
        cursor.execute('SELECT balance, hold_balance FROM balances WHERE user_id = ?', (message.from_user.id,))
        user_balance = cursor.fetchone()
        
        cursor.execute('SELECT currency FROM user_currency WHERE user_id = ?', (message.from_user.id,))
        user_currency_data = cursor.fetchone()
        user_currency = user_currency_data[0] if user_currency_data else 'USD'

        if user_balance:
            balance = math.floor(user_balance[0] * 1000) / 1000
            hold_balance = math.floor(user_balance[1] * 1000) / 1000
            if user_currency != 'USD':
                rate = await get_exchange_rate('USD', user_currency)
                balance_in_currency = math.floor((balance * rate)*1000)/1000
                hold_balance_in_currency = math.floor((hold_balance * rate)*1000)/1000
                await message.answer(f"Ваш текущий баланс: ${balance} / {balance_in_currency} {user_currency}\nБаланс на удержании: ${hold_balance} / {hold_balance_in_currency} {user_currency}")
            else:
                await message.answer(f"Ваш текущий баланс: ${balance}\nБаланс на удержании: ${hold_balance}")
        else:
            await message.answer("Ваш текущий баланс: $0\nБаланс на удержании: $0")
    except Exception as e:
        logging.error(f"Ошибка при отображении баланса: {e}")
        await message.answer("Произошла ошибка при отображении баланса. Попробуйте позже.")

@dp.message(F.text == '🌐 Выбор валюты')
async def select_currency(message: types.Message):
    await message.answer("Выберите валюту для отображения баланса:", reply_markup=currency_keyboard)

@dp.message(lambda message: message.text in currencies)
async def set_currency(message: types.Message):
    selected_currency = message.text
    cursor.execute('INSERT OR REPLACE INTO user_currency (user_id, currency) VALUES (?, ?)', (message.from_user.id, selected_currency))
    conn.commit()
    await message.answer(f"Валюта успешно изменена на {selected_currency}.", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data and c.data.startswith('check'))
async def process_check(callback_query: types.CallbackQuery):
    try:
        data = callback_query.data.split('|')
        temp_id = int(data[1])

        # Извлекаем данные из временной таблицы
        cursor.execute('SELECT login, password FROM temp_check WHERE id = ?', (temp_id,))
        temp_data = cursor.fetchone()

        if temp_data:
            login, password = temp_data
            inline_kb_check = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Рабочий", callback_data=f"result|{temp_id}|working"), 
                 InlineKeyboardButton(text="Не рабочий", callback_data=f"result|{temp_id}|not_working")]
            ])

            # Зачисляем средства на hold баланс
            cursor.execute('INSERT OR IGNORE INTO balances (user_id, balance, hold_balance) VALUES (?, 0, 0)', (callback_query.from_user.id,))
            cursor.execute(f'UPDATE balances SET hold_balance = hold_balance + {ACCRUAL} WHERE user_id = ?', (callback_query.from_user.id,))
            conn.commit()

            await callback_query.answer()
            await bot.send_message(CHECK_CHAT_ID, f"Проверка логина и пароля:\nЛогин: {login}\nПароль: {password}", reply_markup=inline_kb_check)
            await callback_query.message.answer("Сообщение с логином и паролем отправлено для проверки.")
        else:
            await callback_query.message.answer("Ошибка: временные данные не найдены.")
    except Exception as e:
        logging.error(f"Ошибка при проверке учётных данных: {e}")
        await callback_query.message.answer(f"Ошибка отправки сообщения: {e}")

@dp.callback_query(lambda c: c.data and c.data.startswith('result'))
async def process_result(callback_query: types.CallbackQuery, ):
    try:
        data = callback_query.data.split('|')
        temp_id = int(data[1])
        result = data[2]
        result_text = "Рабочий" if result == "working" else "Не рабочий"

        # Извлекаем данные из временной таблицы
        cursor.execute('SELECT user_id, login, password FROM temp_check WHERE id = ?', (temp_id,))
        temp_data = cursor.fetchone()
            
        if temp_data:
            sender_id, login, password = temp_data
            login_gm = temp_data[1]
            login = temp_data[0]

            if result == "working":
                cursor.execute(f'UPDATE balances SET balance = balance + {ACCRUAL} WHERE user_id = ?', (callback_query.from_user.id,))
                conn.commit()
                await bot.send_message(login,f"🎉 Логин: {login_gm} был успешно проверен! На ваш баланс начислено {ACCRUAL}$. Спасибо за вашу работу! 💸")


                # Перевод средств с hold баланса на баланс
                cursor.execute(f'UPDATE balances SET hold_balance = hold_balance - {ACCRUAL}, balance = balance + {ACCRUAL} WHERE user_id = ?', (sender_id,))
                conn.commit()

                # Сохраняем логин и пароль в базу данных со статусом 'working'
                logging.info(f"Сохранение логина {login} и пароля в базу данных")
                cursor.execute('INSERT INTO credentials (user_id, login, password, status) VALUES (?, ?, ?, ?)', (sender_id, login_gm, password, 'working'))
                conn.commit()

                # Увеличиваем счетчик баллов и созданных аккаунтов пользователя
                cursor.execute('SELECT score, created_accounts FROM users WHERE user_id = ?', (sender_id,))
                user = cursor.fetchone()
                if user:
                    new_score = user[0] + 1
                    new_created_accounts = user[1] + 1
                    logging.info(f"Обновление счёта и количества аккаунтов пользователя {sender_id} до {new_score} и {new_created_accounts}")
                    cursor.execute('UPDATE users SET score = ?, created_accounts = ? WHERE user_id = ?', (new_score, new_created_accounts, sender_id))
                else:
                    logging.info(f"Создание записи для нового пользователя {sender_id}")
                    cursor.execute('INSERT INTO users (user_id, score, created_accounts) VALUES (?, ?, ?)', (sender_id, 1, 1))
                conn.commit()


                # print("Открыли базу")
                # cursor2.execute('''
                # INSERT INTO accounts (email, password, is_channel) VALUES (?, ?, ?)
                # ''', (login_gm, password, 0))
                # print("Записали в базу")
                
                # conn2.commit()
                # conn2.close()
            else:
                await bot.send_message(login,f"Аккаунт {login_gm} не работает, зарегистрируйте другой.")
            await callback_query.answer(f"Результат проверки: {result_text}")

            # # Удаляем временные данные
            # cursor.execute('DELETE FROM temp_check WHERE id = ?', (temp_id,))
            # conn.commit()

            # Удаляем сообщение
            await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
        else:
            await callback_query.message.answer("Ошибка: временные данные не найдены.")
    except Exception as e:
        logging.error(f"Ошибка при обработке результата проверки: {e}")

@dp.message(F.text == '💸 Вывести')
async def withdraw_request(message: types.Message):
    await message.answer("Выберите способ вывода:", reply_markup=withdraw_keyboard)

@dp.message(F.text == '🔙 Назад')
async def back_to_main_menu(message: types.Message):
    await message.answer("Возвращение в главное меню.", reply_markup=keyboard)

@dp.message(F.text == '🅿️ Payeer')
async def select_payeer(message: types.Message, state: FSMContext):
    cursor.execute('SELECT balance FROM balances WHERE user_id = ?', (message.from_user.id,))
    user_balance = cursor.fetchone()

    if user_balance and user_balance[0] >= MIN_FOR_CONCLUSION:
        await message.answer(f"Введите сумму, которую хотите вывести (минимальная сумма: ${MIN_FOR_CONCLUSION}):")
        await state.set_state(WithdrawState.awaiting_withdraw_amount)
    else:
        await message.answer(f"У вас недостаточно средств. Минимальная сумма для вывода на Payeer wallet: ${MIN_FOR_CONCLUSION}")

@dp.message(WithdrawState.awaiting_withdraw_amount)
async def process_withdraw_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)

        if amount < MIN_FOR_CONCLUSION:
            await message.answer(f"Минимальная сумма для вывода: ${MIN_FOR_CONCLUSION}. Попробуйте снова.")
        else:
            commission = amount * 0.2
            amount_after_commission = amount - commission
            await state.update_data(amount=amount, amount_after_commission=amount_after_commission)
            await message.answer(f"Комиссия за вывод составляет 20%.\nСумма к выводу с учетом комиссии: ${amount_after_commission:.2f}\nВведите номер вашего кошелька Payeer (например, P12345678):")
            await state.set_state(WithdrawState.awaiting_wallet_number)
    except ValueError:
        await message.answer("Пожалуйста, введите правильную сумму.")

@dp.message(WithdrawState.awaiting_wallet_number)
async def process_wallet_number(message: types.Message, state: FSMContext):
    wallet_number = message.text
    if not is_valid_payeer_wallet(wallet_number):
        await message.answer("Некорректный номер кошелька. Пожалуйста, введите правильный номер (например, P12345678):")
        return

    data = await state.get_data()
    amount = data.get("amount")
    amount_after_commission = data.get("amount_after_commission")

    try:
        cursor.execute('SELECT balance FROM balances WHERE user_id = ?', (message.from_user.id,))
        user_balance = cursor.fetchone()

        if user_balance and user_balance[0] >= amount:
            inline_kb_confirm = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Вывел", callback_data=f"withdraw_done|{message.from_user.id}|{amount}|{amount_after_commission}")],
                [InlineKeyboardButton(text="Невозможно вывести", callback_data=f"withdraw_failed|{message.from_user.id}|{amount}")]
            ])
            await bot.send_message(CHECK_CHAT_ID, f"Запрос на вывод средств:\nПользователь ID: {message.from_user.id}\nСумма: ${amount}\nСумма к выводу с учетом комиссии: ${amount_after_commission:.2f}\nКошелек 🅿️Payeer: {wallet_number}", reply_markup=inline_kb_confirm)
            await message.answer("Ваш запрос на вывод средств отправлен на проверку.")
            # #Выплата реферального бонуса
            # cursor.execute('SELECT referrer_id FROM referrals WHERE user_id = ?', (message.from_user.id,))
            # referrer = cursor.fetchone()
            # if referrer:
            #     referrer_id = referrer[0]
            #     referral_bonus = amount * WITHDRAWAL_PERCENTAGE
            #     cursor.execute('UPDATE balances SET balance = balance + ? WHERE user_id = ?', (referral_bonus, referrer_id))
            #     conn.commit()

            #     # Уведомление реферера
            #     try:
            #         await bot.send_message(referrer_id, f"Вам начислен реферальный бонус в размере {referral_bonus:.2f} USD от вывода средств вашим рефералом.")
            #     except Exception as e:
            #         logging.error(f"Ошибка при отправке уведомления рефереру: {e}")
            
        else:
            await message.answer("Ошибка: недостаточно средств на балансе.")

        await state.clear()
    except Exception as e:
        logging.error(f"Ошибка при подтверждении вывода: {e}")
        await message.answer("Произошла ошибка при подтверждении вывода. Попробуйте позже.")
    finally:
        await state.clear()

@dp.callback_query(lambda c: c.data and c.data.startswith('withdraw_done'))
async def process_withdraw_done(callback_query: types.CallbackQuery):
    try:
        data = callback_query.data.split('|')
        user_id = int(data[1])
        amount = float(data[2])
        amount_after_commission = float(data[3])

        cursor.execute('SELECT balance FROM balances WHERE user_id = ?', (user_id,))
        user_balance = cursor.fetchone()
        if user_balance and user_balance[0] >= amount:
            cursor.execute('UPDATE balances SET balance = balance - ? WHERE user_id = ?', (amount, user_id))
            conn.commit()
            await callback_query.answer("Вывод средств подтвержден.")
            await bot.send_message(user_id, f"Ваш запрос на вывод ${amount} был успешно обработан. На ваш кошелек было отправлено ${amount_after_commission:.2f}.")

        else:
            await callback_query.message.answer("Ошибка: недостаточно средств на балансе.")
        
        # Удаление сообщения
        await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
        
    except Exception as e:
        logging.error(f"Ошибка при обработке вывода средств: {e}")
        await callback_query.message.answer("Произошла ошибка при обработке вывода средств. Попробуйте позже.")

@dp.callback_query(lambda c: c.data and c.data.startswith('withdraw_failed'))
async def process_withdraw_failed(callback_query: types.CallbackQuery):
    try:
        data = callback_query.data.split('|')
        user_id = int(data[1])
        amount = float(data[2])

        await callback_query.answer("Невозможно вывести средства.")
        await bot.send_message(user_id, f"Ваш запрос на вывод ${amount} не может быть обработан.")

        # Удаление сообщения
        await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
        
    except Exception as e:
        logging.error(f"Ошибка при обработке отказа в выводе средств: {e}")
        await callback_query.message.answer("Произошла ошибка при обработке отказа в выводе средств. Попробуйте позже.")