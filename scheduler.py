"""
Scheduler for daily reminders.
Run separately: python scheduler.py
Or integrate with bot.py using asyncio tasks.
"""
import asyncio
import logging
import os
from datetime import datetime, time as dtime

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from dotenv import load_dotenv

load_dotenv()

import database as db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_reminders(bot: Bot):
    """Send reminders for events happening tomorrow."""
    events = await db.get_events_for_reminder(days_ahead=1)
    for event in events:
        user_ids = await db.get_confirmed_user_ids(event["id"])
        date_str = datetime.strptime(event["event_date"], "%Y-%m-%d").strftime("%d.%m.%Y")
        icon = "🏋️" if event["type"] == "training" else "🏒"

        for uid in user_ids:
            try:
                await bot.send_message(
                    uid,
                    f"⏰ <b>Напоминание!</b>\n\n"
                    f"Завтра {icon} <b>{event['title']}</b>\n"
                    f"📅 {date_str} в {event['event_time']}\n"
                    f"👥 Команда: {event['team_name']}\n"
                    f"{'📍 ' + event['location'] if event['location'] else ''}",
                    parse_mode="HTML"
                )
            except TelegramForbiddenError:
                pass
            await asyncio.sleep(0.05)  # Telegram rate limit

    if events:
        logger.info(f"Sent reminders for {len(events)} events")

async def scheduler_loop(bot: Bot):
    """Run reminders every day at 19:00."""
    while True:
        now = datetime.now()
        target = now.replace(hour=19, minute=0, second=0, microsecond=0)
        if now >= target:
            target = target.replace(day=target.day + 1)
        wait_seconds = (target - now).total_seconds()
        logger.info(f"Next reminder check in {wait_seconds/3600:.1f} hours")
        await asyncio.sleep(wait_seconds)
        await send_reminders(bot)

async def main():
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    await db.init_db()
    await scheduler_loop(bot)

if __name__ == "__main__":
    asyncio.run(main())
