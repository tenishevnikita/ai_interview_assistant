import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

from src.bot.handlers import router
from src.config import settings


async def setup_bot_commands(bot: Bot) -> None:
    """Настраивает меню команд бота."""
    commands = [
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="help", description="Показать справку"),
        BotCommand(command="brief", description="Установить краткий стиль ответа"),
        BotCommand(command="detailed", description="Установить подробный стиль ответа"),
        BotCommand(command="clear", description="Очистить контекст диалога"),
    ]
    await bot.set_my_commands(commands)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )

    # Настраиваем меню команд
    await setup_bot_commands(bot)

    dp = Dispatcher()
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
