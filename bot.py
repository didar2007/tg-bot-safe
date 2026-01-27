import json
from datetime import datetime

import telebot
from telebot import types

TOKEN = "8310101212:AAHD5r1vaPljpzK2BGbypLnQVmv5bfMkH64"
WEBAPP_URL = "https://didar2007.github.io/tg-miniapp/?v=6"
ADMIN_ID = 5935991563
ADMIN_USERNAME = "salemhanovvv"  # без @

bot = telebot.TeleBot(TOKEN)


def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("🛒 Открыть магазин", web_app=types.WebAppInfo(url=WEBAPP_URL)))
    kb.add(types.KeyboardButton("📩 Связаться с администратором"))
    return kb


def admin_inline_button():
    ikb = types.InlineKeyboardMarkup()
    ikb.add(types.InlineKeyboardButton("✉️ Написать администратору", url=f"https://t.me/{ADMIN_USERNAME}"))
    return ikb


@bot.message_handler(commands=["start"])
def start(message):
    text = (
        "🔥 *WAKA STORE* 🔥\n\n"
        "💨 *Оригинальные WAKA* — яркий вкус и мощная тяга.\n"
        "🚚 Доставка по городу: *30–60 минут*\n\n"
        "Выбирай действие ниже 👇"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=main_keyboard())


@bot.message_handler(func=lambda m: m.text == "📩 Связаться с администратором")
def contact_admin(message):
    text = (
        "📩 *Связь с администратором*\n\n"
        "Если хочешь уточнить наличие, вкус или доставку — нажми кнопку ниже 👇"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=admin_inline_button())


@bot.message_handler(content_types=["web_app_data"])
def web_app(message):
    raw = message.web_app_data.data
    user = message.from_user
    username = f"@{user.username}" if user.username else "без username"

    try:
        payload = json.loads(raw)
    except Exception:
        payload = None

    # если пришел не JSON
    if not isinstance(payload, dict):
        bot.send_message(
            message.chat.id,
            "✅ *Заказ принят!* Мы скоро свяжемся с вами 💨",
            parse_mode="Markdown"
        )
        bot.send_message(
            ADMIN_ID,
            f"📦 *НОВЫЙ ЗАКАЗ (сырой текст)*\n\n"
            f"👤 Клиент: {user.first_name} ({username})\n"
            f"🆔 ID: `{user.id}`\n\n"
            f"{raw}",
            parse_mode="Markdown"
        )
        return

    phone = (payload.get("phone") or "").strip()
    address = (payload.get("address") or "").strip()
    items = payload.get("items") or []
    total = payload.get("total", None)

    lines = []
    if isinstance(items, list):
        for it in items:
            if isinstance(it, dict):
                name = (it.get("name") or "").strip()
                ru = (it.get("ru") or "").strip()
                qty = int(it.get("qty", 1) or 1)
                price = int(it.get("price", 0) or 0)
                line = f"• *{name}*\n  _{ru}_ ×{qty}"
                if price:
                    line += f" = ₸{price * qty}"
                lines.append(line)
            else:
                lines.append(f"• {str(it)}")
    else:
        lines = [f"• {str(items)}"]

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    admin_text = (
        "🚨 *НОВЫЙ ЗАКАЗ WAKA* 🚨\n\n"
        f"🕒 Время: {now}\n"
        f"👤 Клиент: {user.first_name} ({username})\n"
        f"🆔 ID: `{user.id}`\n"
        f"📱 Телефон: *{phone or '—'}*\n"
        f"🏠 Адрес: *{address or '—'}*\n\n"
        "📦 *Состав заказа:*\n" + ("\n".join(lines) if lines else "• (пусто)")
    )
    if total is not None:
        admin_text += f"\n\n💰 *ИТОГО: ₸{total}*"

    # клиенту — красиво
    user_text = (
        "✅ *Заказ принят!* 🎉\n\n"
        "Спасибо за заказ в *WAKA STORE* 💨\n"
        "Администратор свяжется с вами в ближайшее время.\n\n"
        "Если нужно уточнить детали — напишите администратору 👇"
    )

    bot.send_message(message.chat.id, user_text, parse_mode="Markdown", reply_markup=admin_inline_button())
    bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")


bot.polling(none_stop=True)
