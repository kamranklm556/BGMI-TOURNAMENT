# -*- coding: utf-8 -*-
# KLM Giveaway + Referral Coins Bot (with username Leaderboard)
# python-telegram-bot == 20.3

import sqlite3
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ========= SETTINGS =========
BOT_TOKEN = 8379953073:AAGQIjLYE0nZ6mX1fW_vIBA5FKsgLT11pec
CHANNEL_USERNAME = "@KLMgiveway"
ADMIN_ID = 6703290044
COINS_PER_INVITE = 10
DB_FILE = "klm_bot.db"

# ========= DB HELPERS =========
def db_execute(query, params=(), fetch=False, many=False):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    if many:
        cur.executemany(query, params)
    else:
        cur.execute(query, params)
    rows = cur.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return rows

def init_db():
    db_execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name    TEXT,
            coins   INTEGER DEFAULT 0,
            invites INTEGER DEFAULT 0
        )
    """)
    db_execute("""
        CREATE TABLE IF NOT EXISTS participants (
            user_id INTEGER PRIMARY KEY
        )
    """)

def ensure_user(user_id: int, name: str):
    # create user if not exists + keep latest name
    db_execute(
        "INSERT OR IGNORE INTO users (user_id, name, coins, invites) VALUES (?, ?, 0, 0)",
        (user_id, name),
    )
    db_execute("UPDATE users SET name = ? WHERE user_id = ?", (name, user_id))

def add_referral_reward(ref_id: int):
    db_execute("UPDATE users SET coins = coins + ?, invites = invites + 1 WHERE user_id = ?",
               (COINS_PER_INVITE, ref_id))

def user_balance(user_id: int):
    rows = db_execute("SELECT coins, invites, name FROM users WHERE user_id = ?", (user_id,), fetch=True)
    if rows:
        c, i, n = rows[0]
        return c, i, n or ""
    return 0, 0, ""

def top_users(limit=10):
    return db_execute(
        "SELECT user_id, name, coins FROM users WHERE coins > 0 ORDER BY coins DESC, user_id ASC LIMIT ?",
        (limit,),
        fetch=True
    )

def add_participant(user_id: int):
    db_execute("INSERT OR IGNORE INTO participants (user_id) VALUES (?)", (user_id,))

def all_participants():
    rows = db_execute("SELECT user_id FROM participants", fetch=True)
    return [r[0] for r in rows]

# ========= COMMANDS =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    uid = update.effective_user.id
    name = update.effective_user.full_name

    ensure_user(uid, name)

    # Referral ( ?start=ref_<user_id> )
    if args:
        try:
            ref_id = int(args[0].replace("ref_", ""))
            if ref_id != uid:
                # make sure referrer exists
                ensure_user(ref_id, (await context.bot.get_chat(ref_id)).full_name if ref_id else "User")
                add_referral_reward(ref_id)
                # notify referrer (ignore if user blocked the bot)
                try:
                    await context.bot.send_message(
                        ref_id,
                        f"🎉 A new user joined through your referral!\n💰 +{COINS_PER_INVITE} KLM Coins"
                    )
                except:
                    pass
        except:
            pass

    ref_link = f"https://t.me/{context.bot.username}?start=ref_{uid}"

    await update.message.reply_text(
        "🎁 *Welcome to KLM Giveaway & Referral Bot!*\n\n"
        f"📢 Channel: {CHANNEL_USERNAME}\n"
        f"💰 For every valid invite, you earn *{COINS_PER_INVITE} KLM Coins*.\n\n"
        f"🔗 *Your Referral Link:*\n{ref_link}\n\n"
        "Commands:\n"
        "/join - Join the giveaway\n"
        "/mycoins - Check your balance\n"
        "/leaderboard - Top players (username + coins)\n"
        "/winner - Declare winner (Admin only)",
        parse_mode="Markdown"
    )

participants_cache = []  # only for fast check in-memory