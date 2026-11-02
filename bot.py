import asyncio
import datetime
import logging
import random
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice

# --- НАСТРОЙКИ ---
TOKEN = "9074743834:AAG5cG3Nkefau5DLIRJwDHXYB8qJNYzeM0g"
ADMIN_ID = 8947352478  # Твой ID администратора

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Инициализация базы данных SQLite
conn = sqlite3.connect("casino.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance INTEGER DEFAULT 0,
    invited_by INTEGER,
    refs_count INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0,
    last_bonus TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS winners_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    prize_name TEXT,
    prize_value INTEGER,
    case_cost INTEGER,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS stats (
    key TEXT PRIMARY KEY,
    value INTEGER
)
""")
cursor.execute(
    "INSERT OR IGNORE INTO stats (key, value) VALUES ('total_income', 0)"
)
conn.commit()

# --- ЭКОНОМИКА И ШАНСЫ ---
CASE_10 = [
    {"name": "❌ Мимо", "value": 0, "weight": 7500},
    {"name": "💖 Сердечко (15⭐)", "value": 15, "weight": 1000},
    {"name": "🌹 Роза (25⭐)", "value": 25, "weight": 500},
    {"name": "🎁 Подарочная коробка (25⭐)", "value": 25, "weight": 400},
    {"name": "🎂 Торт (50⭐)", "value": 50, "weight": 250},
    {"name": "💐 Букет тюльпанов (50⭐)", "value": 50, "weight": 150},
    {"name": "🚀 Ракета (50⭐)", "value": 50, "weight": 100},
    {"name": "🏆 Кубок (100⭐)", "value": 100, "weight": 80},
    {"name": "💍 Колечко (100⭐)", "value": 100, "weight": 20},
]

CASE_35 = [
    {"name": "❌ Мимо", "value": 0, "weight": 5000},
    {"name": "🌹 Роза (25⭐)", "value": 25, "weight": 3500},
    {"name": "💎 Алмаз (50⭐)", "value": 50, "weight": 500},
    {"name": "🎁 Подарочная коробка (25⭐)", "value": 25, "weight": 400},
    {"name": "🎂 Торт (50⭐)", "value": 50, "weight": 250},
    {"name": "💐 Букет тюльпанов (50⭐)", "value": 50, "weight": 200},
    {"name": "🚀 Ракета (50⭐)", "value": 50, "weight": 100},
    {"name": "🏆 Кубок (100⭐)", "value": 100, "weight": 30},
    {"name": "💍 Колечко (100⭐)", "value": 100, "weight": 20},
]


def spin_case(case_type: int):
  prizes = CASE_10 if case_type == 10 else CASE_35
  weights = [p["weight"] for p in prizes]
  return random.choices(prizes, weights=weights, k=1)[0]


# --- ГЛАВНОЕ МЕНЮ И СТАРТ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
  user_id = message.from_user.id
  username = message.from_user.username or message.from_user.first_name

  cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
  banned = cursor.fetchone()
  if banned and banned[0] == 1:
    await message.answer("❌ Вы заблокированы в этом боте.")
    return

  args = message.text.split()
  if len(args) > 1 and args[1].isdigit():
    referrer_id = int(args[1])
    if referrer_id != user_id:
      cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
      is_new = cursor.fetchone()
      if not is_new:
        cursor.execute(
            "UPDATE users SET refs_count = refs_count + 1 WHERE user_id = ?",
            (referrer_id,),
        )
        conn.commit()

  cursor.execute(
      "INSERT OR IGNORE INTO users (user_id, username, balance) VALUES (?, ?,"
      " 0)",
      (user_id, username),
  )
  cursor.execute(
      "UPDATE users SET username = ? WHERE user_id = ?", (username, user_id)
  )
  conn.commit()

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="📦 Кейс за 10 ⭐", callback_data="buy_10"
              ),
              InlineKeyboardButton(
                  text="🚀 Премиум за 35 ⭐", callback_data="buy_35"
              ),
          ],
          [
              InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
              InlineKeyboardButton(
                  text="💳 Пополнить баланс", callback_data="topup_menu"
              ),
          ],
          [
              InlineKeyboardButton(
                  text="👥 Рефералы", callback_data="ref_menu"
              ),
              InlineKeyboardButton(
                  text="🎁 Ежедневный бонус", callback_data="daily_bonus"
              ),
          ],
          [
              InlineKeyboardButton(
                  text="ℹ️ Помощь (Help)", callback_data="help_menu"
              )
          ],
      ]
  )

  await message.answer(
      "🎰 **Добро пожаловать в магазин редких подарков!**\n\nВыбирай кейс,"
      " запускай рулетку и выбивай топовые награды:",
      reply_markup=keyboard,
      parse_mode="Markdown",
  )


# --- СПРАВКА /HELP ДЛЯ ВСЕХ ---
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
  text = (
      "ℹ️ **Как пользоваться ботом:**\n\n1. **Баланс:** Пополняй внутренний"
      " баланс через меню (в валюте Telegram Stars ⭐).\n2. **Кейсы:** Открывай"
      " кейсы за 10 или 35 звезд. Внутри тебя ждут крутые призы и подарки!\n3."
      " **Выигрыши:** Все призы стоимостью от 15 звезд записываются в систему."
      " Для получения выплаты напиши администратору: **@RoolGiftsP**.\n4."
      " **Рефералы:** Приглашай друзей по своей ссылке и получай бонусы.\n5."
      " **Бонус:** Забирай ежедневный бонус раз в 24 часа!\n\n📌"
      " *Команды:*\n• `/start` — Главное меню\n• `/profile` — Твой профиль\n•"
      " `/mywins` — Твои последние выигрыши\n• `/help` — Эта справка"
  )
  await message.answer(text, parse_mode="Markdown")


@dp.callback_query(F.data == "help_menu")
async def cb_help(callback: types.CallbackQuery):
  text = (
      "ℹ️ **Как пользоваться ботом:**\n\n1. **Баланс:** Пополняй внутренний"
      " баланс через меню (в валюте Telegram Stars ⭐).\n2. **Кейсы:** Открывай"
      " кейсы за 10 или 35 звезд. Внутри тебя ждут крутые призы и подарки!\n3."
      " **Выигрыши:** Все призы стоимостью от 15 звезд записываются в систему."
      " Для получения выплаты напиши администратору: **@RoolGiftsP**.\n4."
      " **Рефералы:** Приглашай друзей по своей ссылке и получай бонусы.\n5."
      " **Бонус:** Забирай ежедневный бонус раз в 24 часа!"
  )
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text="◀️ Назад", callback_data="back_home")]
      ]
  )
  await callback.message.edit_text(
      text, parse_mode="Markdown", reply_markup=keyboard
  )
  await callback.answer()


# --- ЛИЧНЫЕ ВЫИГРЫШИ ПОЛЬЗОВАТЕЛЯ (/mywins) ---
@dp.message(Command("mywins"))
async def cmd_mywins(message: types.Message):
  user_id = message.from_user.id
  cursor.execute(
      "SELECT prize_name, prize_value, date FROM winners_log WHERE user_id = ?"
      " ORDER BY id DESC LIMIT 10",
      (user_id,),
  )
  rows = cursor.fetchall()

  text = "🏆 **Твои последние выигрыши:**\n\n"
  if not rows:
    text += "У тебя пока нет крупных выигрышей. Испытай удачу в кейсах!"
  else:
    for row in rows:
      p_name, p_val, date = row
      text += f"• **{p_name}** ({p_val}⭐) — `{date}`\n"
    text += (
        "\n📨 Для получения приза отправь скриншот/информацию сюда:"
        " **@RoolGiftsP**"
    )

  await message.answer(text, parse_mode="Markdown")


# --- ПРОФИЛЬ ---
@dp.callback_query(F.data == "profile")
async def cb_profile(callback: types.CallbackQuery):
  user_id = callback.from_user.id
  cursor.execute(
      "SELECT balance, refs_count FROM users WHERE user_id = ?", (user_id,)
  )
  row = cursor.fetchone()
  balance = row[0] if row else 0
  refs = row[1] if row else 0

  text = (
      f"👤 **Твой профиль:**\n\n🆔 ID: `{user_id}`\n💰 Внутренний баланс:"
      f" **{balance} ⭐**\n👥 Приглашено друзей: **{refs}**\n\n🎁 *Награда за"
      " рефералов:*\n• 7 друзей = 1 спин на 10⭐\n• 15 друзей = 1 спин на 35⭐"
  )
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text="◀️ Назад", callback_data="back_home")]
      ]
  )
  await callback.message.edit_text(
      text, parse_mode="Markdown", reply_markup=keyboard
  )
  await callback.answer()


@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
  await cb_profile(
      types.CallbackQuery(
          id="0",
          from_user=message.from_user,
          message=message,
          data="profile",
      )
  )


# --- РЕФЕРАЛЬНАЯ СИСТЕМА ---
@dp.callback_query(F.data == "ref_menu")
async def cb_ref(callback: types.CallbackQuery):
  user_id = callback.from_user.id
  bot_info = await bot.get_me()
  ref_link = f"https://t.me/{bot_info.username}?start={user_id}"

  cursor.execute("SELECT refs_count FROM users WHERE user_id = ?", (user_id,))
  refs = cursor.fetchone()[0]

  text = (
      f"👥 **Реферальная система**\n\nПриглашай друзей по своей ссылке и получай"
      f" бонусы!\n🔗 Твоя ссылка:\n`{ref_link}`\n\n📊 Твои рефералы: **{refs}"
      " чел.**"
  )
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text="◀️ Назад", callback_data="back_home")]
      ]
  )
  await callback.message.edit_text(
      text, parse_mode="Markdown", reply_markup=keyboard
  )
  await callback.answer()


# --- ЕЖЕДНЕВНЫЙ БОНУС ---
@dp.callback_query(F.data == "daily_bonus")
async def cb_daily(callback: types.CallbackQuery):
  user_id = callback.from_user.id
  today = str(datetime.date.today())

  cursor.execute("SELECT last_bonus FROM users WHERE user_id = ?", (user_id,))
  row = cursor.fetchone()
  if row and row[0] == today:
    await callback.answer(
        "⏳ Ты уже забирал бонус сегодня! Приходи завтра.", show_alert=True
    )
    return

  bonus = random.randint(1, 5)
  cursor.execute(
      "UPDATE users SET balance = balance + ?, last_bonus = ? WHERE user_id ="
      " ?",
      (bonus, today, user_id),
  )
  conn.commit()

  await callback.answer(
      f"🎉 Ура! Ты получил ежедневный бонус: +{bonus} ⭐", show_alert=True
  )


# --- МЕНЮ ПОПОЛНЕНИЯ БАЛАНСА ---
@dp.callback_query(F.data == "topup_menu")
async def cb_topup(callback: types.CallbackQuery):
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="💳 Пополнить 50 ⭐", callback_data="pay_50"
              ),
              InlineKeyboardButton(
                  text="💳 Пополнить 100 ⭐", callback_data="pay_100"
              ),
          ],
          [
              InlineKeyboardButton(
                  text="💳 Пополнить 250 ⭐", callback_data="pay_250"
              )
          ],
          [InlineKeyboardButton(text="◀️ Назад", callback_data="back_home")],
      ]
  )
  await callback.message.edit_text(
      "💳 **Пополнение баланса**\n\nВыбери сумму пополнения. Звезды зачислятся на"
      " твой внутренний баланс для быстрых прокрутов!",
      parse_mode="Markdown",
      reply_markup=keyboard,
  )
  await callback.answer()


@dp.callback_query(F.data.startswith("pay_"))
async def process_topup_invoice(callback: types.CallbackQuery):
  amount = int(callback.data.split("_")[1])
  prices = [LabeledPrice(label=f"Пополнение {amount} ⭐", amount=amount)]

  await callback.bot.send_invoice(
      chat_id=callback.message.chat.id,
      title=f"Пополнение баланса на {amount} ⭐",
      description="Зачисление звезд на внутренний баланс бота.",
      payload=f"topup_{amount}",
      provider_token="",
      currency="XTR",
      prices=prices,
  )
  await callback.answer()


@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: types.PreCheckoutQuery):
  await pre_checkout_query.bot.answer_pre_checkout_query(
      pre_checkout_query.id, ok=True
  )


@dp.message(F.successful_payment)
async def successful_payment_handler(message: types.Message):
  payment_data = message.successful_payment.invoice_payload
  user_id = message.from_user.id

  if "topup_" in payment_data:
    amount = int(payment_data.split("_")[1])
    cursor.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
        (amount, user_id),
    )
    cursor.execute(
        "UPDATE stats SET value = value + ? WHERE key = 'total_income'",
        (amount,),
    )
    conn.commit()
    await message.answer(
        f"✅ Баланс успешно пополнен на **{amount} ⭐**!", parse_mode="Markdown"
    )

  elif "case_" in payment_data:
    case_cost = 10 if "10" in payment_data else 35
    cursor.execute(
        "UPDATE stats SET value = value + ? WHERE key = 'total_income'",
        (case_cost,),
    )
    conn.commit()
    await execute_spin(message, case_cost)


# --- ИГРОВОЙ ПРОЦЕСС ---
@dp.callback_query(F.data.in_(["buy_10", "buy_35"]))
async def process_case_click(callback: types.CallbackQuery):
  user_id = callback.from_user.id
  cost = 10 if callback.data == "buy_10" else 35

  cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
  row = cursor.fetchone()
  balance = row[0] if row else 0

  if balance >= cost:
    cursor.execute(
        "UPDATE users SET balance = balance - ? WHERE user_id = ?",
        (cost, user_id),
    )
    cursor.execute(
        "UPDATE stats SET value = value + ? WHERE key = 'total_income'", (cost,)
    )
    conn.commit()

    await callback.message.delete()
    await execute_spin(callback.message, cost)
  else:
    title = "📦 Кейс за 10 ⭐" if cost == 10 else "🚀 Премиум кейс за 35 ⭐"
    prices = [LabeledPrice(label=title, amount=cost)]
    await callback.bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=title,
        description=(
            "Недостаточно средств на балансе. Оплатите счет напрямую."
        ),
        payload=f"case_{cost}",
        provider_token="",
        currency="XTR",
        prices=prices,
    )
  await callback.answer()


async def execute_spin(message: types.Message, case_cost: int):
  user_id = message.from_user.id
  username = message.from_user.username or message.from_user.first_name

  spin_msg = await message.answer(
      "🔄 **Барабан крутится...**\n*Ловим удачу за хвост!* 🎯",
      parse_mode="Markdown",
  )
  await asyncio.sleep(1.5)

  result = spin_case(case_cost)

  cursor.execute(
      "UPDATE users SET balance = balance + ? WHERE user_id = ?",
      (result["value"], user_id),
  )
  conn.commit()

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="🔄 Крутить еще", callback_data=f"buy_{case_cost}"
              ),
              InlineKeyboardButton(text="🏠 В меню", callback_data="back_home"),
          ]
      ]
  )

  if result["value"] > 0:
    await spin_msg.edit_text(
        f"🎉 **Поздравляем с победой!**\n\n🎁 Тебе выпал приз:"
        f" **{result['name']}**\n💰 Стоимость: **{result['value']} звезд**"
        f" зачислена на баланс!\n\n📨 Для получения выплаты напиши сюда:"
        " **@RoolGiftsP**",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
  else:
    await spin_msg.edit_text(
        "❌ **Эх, мимо!**\n\nВ этот раз удача обошла стороной. Попробуй снова!",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

  if result["value"] >= 15:
    cursor.execute(
        "INSERT INTO winners_log (user_id, username, prize_name, prize_value,"
        " case_cost) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, result["name"], result["value"], case_cost),
    )
    conn.commit()


@dp.callback_query(F.data == "back_home")
async def cb_back(callback: types.CallbackQuery):
  await callback.message.delete()
  await cmd_start(callback.message)


# --- АДМИНСКАЯ ПАНЕЛЬ И КОМАНДЫ ---
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
  if message.from_user.id != ADMIN_ID:
    return

  cursor.execute("SELECT value FROM stats WHERE key = 'total_income'")
  income = cursor.fetchone()[0]
  cursor.execute("SELECT SUM(prize_value) FROM winners_log")
  payout = cursor.fetchone()[0] or 0
  profit = income - payout

  text = (
      f"👑 **Админ-панель управления**\n\n📥 Доход кассы: **{income} ⭐**\n📤"
      f" Выплаты: **{payout} ⭐**\n💎 Чистая прибыль: **{profit} ⭐**\n\n🛠"
      f" **Доступные команды:**\n• `/give @username сумма` — выдать баланс"
      " игроку\n• `/ban @username` — заблокировать игрока\n• `/unban"
      " @username` — разблокировать игрока\n• `/wins` — посмотреть статистику"
      " выигрышей и юзеров\n• `/broadcast текст` — рассылка всем"
      " пользователям"
  )
  await message.answer(text, parse_mode="Markdown")


@dp.message(Command("give"))
async def cmd_give(message: types.Message):
  if message.from_user.id != ADMIN_ID:
    return
  args = message.text.split()
  if len(args) < 3:
    await message.answer(
        "⚠️ Использование: `/give @username сумма`", parse_mode="Markdown"
    )
    return
  target_username = args[1].replace("@", "")
  amount = int(args[2])

  cursor.execute(
      "UPDATE users SET balance = balance + ? WHERE username = ?",
      (amount, target_username),
  )
  conn.commit()
  await message.answer(
      f"✅ Пользователю @{target_username} успешно начислено **{amount} ⭐** на"
      " баланс!",
      parse_mode="Markdown",
  )


@dp.message(Command("ban"))
async def cmd_ban(message: types.Message):
  if message.from_user.id != ADMIN_ID:
    return
  args = message.text.split()
  if len(args) < 2:
    await message.answer(
        "⚠️ Использование: `/ban @username`", parse_mode="Markdown"
    )
    return
  target = args[1].replace("@", "")
  cursor.execute("UPDATE users SET is_banned = 1 WHERE username = ?", (target,))
  conn.commit()
  await message.answer(f"🚫 Пользователь @{target} заблокирован.")


@dp.message(Command("unban"))
async def cmd_unban(message: types.Message):
  if message.from_user.id != ADMIN_ID:
    return
  args = message.text.split()
  if len(args) < 2:
    await message.answer(
        "⚠️ Использование: `/unban @username`", parse_mode="Markdown"
    )
    return
  target = args[1].replace("@", "")
  cursor.execute("UPDATE users SET is_banned = 0 WHERE username = ?", (target,))
  conn.commit()
  await message.answer(f"✅ Пользователь @{target} разблокирован.")


@dp.message(Command("wins"))
async def cmd_wins(message: types.Message):
  if message.from_user.id != ADMIN_ID:
    return

  cursor.execute(
      "SELECT username, user_id, prize_name, prize_value, date FROM winners_log"
      " ORDER BY id DESC LIMIT 15"
  )
  rows = cursor.fetchall()

  text = "🏆 **Последние победители для выплат (@RoolGiftsP):**\n\n"
  if not rows:
    text += "Пока нет крупных выигрышей."
  else:
    for row in rows:
      uname, u_id, p_name, p_val, date = row
      user_mention = f"@{uname}" if uname else f"ID: `{u_id}`"
      text += (
          f"• {user_mention} (`{u_id}`)\n  🎁 Выиграл: **{p_name}**"
          f" ({p_val}⭐)\n  🕒 `{date}`\n\n"
      )

  await message.answer(text, parse_mode="Markdown")


@dp.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message):
  if message.from_user.id != ADMIN_ID:
    return
  text_parts = message.text.split(maxsplit=1)
  if len(text_parts) < 2:
    await message.answer("⚠️ Укажи текст для рассылки.", parse_mode="Markdown")
    return

  broadcast_text = text_parts[1]
  cursor.execute("SELECT user_id FROM users")
  users = cursor.fetchall()

  success = 0
  for (u_id,) in users:
    try:
      await bot.send_message(u_id, broadcast_text)
      success += 1
    except Exception:
      pass
  await message.answer(f"📢 Рассылка завершена. Доставлено: {success}")


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  asyncio.run(dp.start_polling(bot))