import asyncio
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage

API_TOKEN = '7331960769:AAFNnPKs1NOcWzQBgx47f0Mhsk0qClWovIc'

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

async def get_user_info(user_id: int):
    user = await bot.get_chat(user_id)
    return user

@router.message(Command('get_user_info'))
async def send_user_info(message: Message):
    try:
        user_id = int(message.text.split(' ', 1)[1])
        user = await get_user_info(user_id)
        await message.reply(f"User info:\nID: {user.id}\nName: {user.full_name}\nUsername: {user.username}")
    except (IndexError, ValueError):
        await message.reply("Please provide a valid user ID.")
    except Exception as e:
        await message.reply(f"An error occurred: {e}")

async def on_startup(bot: Bot):
    print("Bot started")

async def main():
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, on_startup=on_startup)

if __name__ == '__main__':
    asyncio.run(main())
