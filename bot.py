import requests
import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext
from telegram.ext.filters import TEXT
from datetime import datetime

# API URL
API_URL = "https://www.tekika.io/api/nft/nft-xp?pwd=VZSnM2as9wKwqeE"

# Date Ranges for Months
MONTH_1_START = datetime(2025, 1, 10)
MONTH_1_END = datetime(2025, 2, 10)
MONTH_2_START = datetime(2025, 2, 11)
MONTH_2_END = datetime(2025, 3, 10)
MONTH_3_START = datetime(2025, 3, 11)
MONTH_3_END = datetime(2025, 4, 10)

# Track active sessions
active_sessions = {}

# Fetch data from API and calculate totals
def fetch_data():
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        data = response.json()

        total_season2_tekika = 0
        total_xp = 0

        for item in data:
            total_xp += int(item.get("XP", 0))  # Add XP
            if item.get("seasonIndex") == 2:
                total_season2_tekika += 1  # Count seasonIndex 2 Tekika

        return total_season2_tekika, total_xp
    except Exception as e:
        raise RuntimeError(f"Error fetching API data: {e}")

# Determine the month based on today's date
def determine_month():
    today = datetime.now()
    if MONTH_1_START <= today <= MONTH_1_END:
        return "Month 1"
    elif MONTH_2_START <= today <= MONTH_2_END:
        return "Month 2"
    elif MONTH_3_START <= today <= MONTH_3_END:
        return "Month 3"
    else:
        return None

# Perform calculation based on the selected month and carry-over logic
def calculate_share(user_xp, total_season2_tekika, total_xp, month):
    pool = 0
    month_1_users = 10000
    month_2_users = 15000
    
    if month == "Month 1":
        tier1 = min(total_season2_tekika, 10000)
        pool += tier1 * 8
        if total_season2_tekika > 10000:
            tier2 = min(total_season2_tekika - 10000, 10000)
            pool += tier2 * 6
        if total_season2_tekika > 20000:
            tier3 = min(total_season2_tekika - 20000, 10000)
            pool += tier3 * 5
        month_1_share = pool / 3
        pool = month_1_share

    elif month == "Month 2":
        new_users_month_2 = total_season2_tekika - month_1_users
        tier1 = min(new_users_month_2, 10000)
        pool += tier1 * 8
        if new_users_month_2 > 10000:
            tier2 = min(new_users_month_2 - 10000, 10000)
            pool += tier2 * 6
        if new_users_month_2 > 20000:
            tier3 = min(new_users_month_2 - 20000, 10000)
            pool += tier3 * 5
        month_1_share = (month_1_users * 8) / 3
        pool = pool / 2

    elif month == "Month 3":
        new_users_month_3 = total_season2_tekika - month_2_users
        tier1 = min(new_users_month_3, 10000)
        pool += tier1 * 8
        if new_users_month_3 > 10000:
            tier2 = min(new_users_month_3 - 10000, 10000)
            pool += tier2 * 6
        if new_users_month_3 > 20000:
            tier3 = min(new_users_month_3 - 20000, 10000)
            pool += tier3 * 5
        month_1_share = (month_1_users * 8) / 3
        month_2_share = ((month_2_users - month_1_users) * 8) / 2
        pool += month_1_share + month_2_share

    multiplier = pool / total_xp if total_xp > 0 else 0
    user_share = user_xp * multiplier

    return round(pool, 2), round(multiplier, 10), round(user_share, 2)

# Handle /start command
async def start(update: Update, context: CallbackContext) -> None:
    global active_sessions
    user_id = update.effective_user.id
    if user_id in active_sessions:
        await update.message.reply_text("You already have an active session.")
        return

    active_sessions[user_id] = True
    await update.message.reply_text(
        "Welcome! Please provide your XP to calculate your reward. You have 30 seconds."
    )

    # Timeout logic
    for _ in range(30):
        await asyncio.sleep(1)
        if user_id not in active_sessions:
            return

    # If no input is received, clear the session
    await update.message.reply_text("Session timed out. Please restart by typing /XP.")
    del active_sessions[user_id]

# Handle user XP input
async def handle_xp(update: Update, context: CallbackContext) -> None:
    global active_sessions
    user_id = update.effective_user.id

    if user_id not in active_sessions:
        await update.message.reply_text("Please start by typing /XP.")
        return

    try:
        user_xp = int(update.message.text)
        total_season2_tekika, total_xp = fetch_data()
        month = determine_month()
        if not month:
            await update.message.reply_text("We're outside the supported date ranges.")
            return

        total_pool, multiplier, user_share = calculate_share(user_xp, total_season2_tekika, total_xp, month)
        await update.message.reply_text(
            f"Total $TLOS pool: ${total_pool*3:.0f}\n\n"
            f"Results for {month}:\n"
            f"Total $TLOS Pool divided by 3: ${total_pool}\n"
            f"Total Mints: {total_season2_tekika}\n"
            f"Your Tekika Reward: ${user_share:.2f}\n\n"
            f"One third of month 1 total prize pool will be added to the start of month 2 and another third to the start of month 3"
        )

        # Clear session after response
        del active_sessions[user_id]

    except ValueError:
        await update.message.reply_text("Please enter a valid number for your XP.")
    except RuntimeError as e:
        await update.message.reply_text(f"Error: {e}")

# Main function
def main():
    TOKEN = os.getenv("YOUR_BOT_TOKEN")
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("XP", start))
    application.add_handler(MessageHandler(TEXT, handle_xp))

    application.run_polling()

if __name__ == "__main__":
    main()
