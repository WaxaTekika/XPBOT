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

# Track active sessions (Users must type /XP to restart)
active_sessions = set()

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

# Determine the current month
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

# Perform calculations based on user XP
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
        pool = pool / 3

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

    multiplier = pool / total_xp if total_xp > 0 else 0
    user_share = user_xp * multiplier

    return round(pool, 2), round(multiplier, 10), round(user_share, 2)

# Start Command (/XP)
async def start(update: Update, context: CallbackContext) -> None:
    global active_sessions
    user_id = update.effective_user.id

    # Allow the user to start interaction only if they're not already in session
    if user_id in active_sessions:
        await update.message.reply_text("You already started a session. Please enter your XP or wait for the response.")
        return

    active_sessions.add(user_id)
    await update.message.reply_text(
        "Welcome! Please provide your XP to calculate your reward."
    )

# Handle XP Input
async def handle_xp(update: Update, context: CallbackContext) -> None:
    global active_sessions
    user_id = update.effective_user.id

    # If user is not in an active session, ignore input until they type /XP
    if user_id not in active_sessions:
        await update.message.reply_text("Please start a session by typing /XP.")
        return

    try:
        user_xp = int(update.message.text)
        total_season2_tekika, total_xp = fetch_data()
        month = determine_month()
        if not month:
            await update.message.reply_text("We're outside the supported date ranges.")
            return

        total_pool, multiplier, user_share = calculate_share(user_xp, total_season2_tekika, total_xp, month)

        # Send result
        await update.message.reply_text(
            f"Total $TLOS pool: ${total_pool*3:.0f}\n\n"
            f"Results for {month}:\n"
            f"Total $TLOS Pool divided by 3: ${total_pool}\n"
            f"Total Mints: {total_season2_tekika}\n"
            f"Your Tekika Reward: ${user_share:.2f}\n\n"
            f"One third of month 1 total prize pool will be added to the start of month 2 and another third to the start of month 3"
        )

        # REMOVE USER FROM ACTIVE SESSION IMMEDIATELY AFTER RESPONSE
        active_sessions.remove(user_id)

    except ValueError:
        await update.message.reply_text("Please enter a valid number for your XP.")
    except RuntimeError as e:
        await update.message.reply_text(f"Error: {e}")

# Main function
def main():
    TOKEN = os.getenv("YOUR_BOT_TOKEN")
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("XP", start))  # User must type /XP to start
    application.add_handler(MessageHandler(TEXT, handle_xp))  # Process XP input

    application.run_polling()

if __name__ == "__main__":
    main()
