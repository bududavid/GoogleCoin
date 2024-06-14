import asyncio
from DATA import API_TOKEN
from handlers import register_handlers, dp, bot
from database import create_tables


# Запуск бота
async def main():
    create_tables()  
    register_handlers(dp)
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
