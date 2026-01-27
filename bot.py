import os
import json
from datetime import datetime

import telebot
from telebot import types


def must_get_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Переменная окружения {name} не задана. "
            f"Добавь её в Railway → Variables."
        )
    return value


# === Railway Variables ===
TOKEN = must_get_env("TOKEN")
WEBAPP_URL = must_get_env("WEBAPP_URL")
ADMIN_ID = int(must_get_env("ADMIN_ID"))

# Админ username (без @). Можно не задавать, тогда кнопка не появится.
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "").strip().lstrip("@")

bot = telebot.TeleBot(TOKEN)


def build_main_keyboard():
    """
    ReplyKeyboard (нижняя панель кнопок):
    - открыть магазин (WebApp)
    - связаться с администратором (если задан ADMIN_USERNAME)
    """
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    webapp_btn = types.KeyboardButton(
        "🛒 Открыть магазин",
        web_app=types.WebAppInfo(url=WEBAPP_URL),
    )
    kb.add(webapp_btn)

    if ADMIN_USERNAME:
        kb.add(types.KeyboardButton("📩 Связаться с администратором"))

    return kb


def build_inline_contact():
    """
    Inline-кнопка (под сообщением): открыть чат с админом.
    """
    if not ADMIN_USERNAME:
        return None

    ikb = types.InlineKeyboardMarkup()
    ikb.add(
        types.InlineKeyboardButton(
            "📩 Написать администратору",
            url=f"https://t.me/{ADMIN_USERNAME}"
        )
    )
    return ikb


def safe_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return default


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Нажми кнопку ниже, чтобы открыть магазин:",
        reply_markup=build_main_keyboard()
    )


@bot.message_handler(commands=["myid"])
def myid(message):
    bot.send_message(message.chat.id, f"Твой ID: {message.from_user.id}")


@bot.message_handler(func=lambda m: m.text == "📩 Связаться с администратором")
def contact_admin(message):
    """
    Кнопка в чате (ReplyKeyboard): отправляем пользователю сообщение с inline-кнопкой,
    которая откроет чат с админом.
    """
    if not ADMIN_USERNAME:
        bot.send_message(message.chat.id, "Администратор не настроен.")
        return

    bot.send_message(
        message.chat.id,
        "Нажми кнопку ниже, чтобы написать администратору:",
        reply_markup=build_inline_contact()
    )


@bot.message_handler(content_types=["web_app_data"])
def web_app(message):
    raw = message.web_app_data.data

    user = message.from_user
    username = f"@{user.username}" if user.username else "нет username"

    # Пытаемся разобрать JSON
    try:
        payload = json.loads(raw)
    except Exception:
        payload = None

    # Если пришёл не JSON — отправим админу как есть
    if not isinstance(payload, dict):
        bot.send_message(message.chat.id, "✅ Заказ принят! Мы скоро свяжемся с вами.")
        bot.send_message(
            ADMIN_ID,
            "📦 НОВЫЙ ЗАКАЗ (сырой текст)\n"
            f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"От: {user.first_name} (id: {user.id}, {username})\n\n"
            f"{raw}"
        )
        return

    # ОЖИДАЕМЫЙ ФОРМАТ ОТ ТВОЕГО HTML СЕЙЧАС:
    # {
    #   "phone": "...",
    #   "address": "...",
    #   "items": [{catId,index,name,ru,price,qty}, ...],
    #   "total": 12345
    # }
    phone = (payload.get("phone") or "").strip()
    address = (payload.get("address") or "").strip()
    items = payload.get("items") or []
    total = payload.get("total", None)

    # Собираем строки заказа
    lines = []
    if isinstance(items, list):
        for it in items:
            if isinstance(it, dict):
                name = (it.get("name") or "").strip()
                ru = (it.get("ru") or "").strip()
                qty = safe_int(it.get("qty", 1), 1)
                price = safe_int(it.get("price", 0), 0)

                line = f"• {name}"
                if ru:
                    line += f" — {ru}"
                line += f" ×{qty}"
                if price:
                    line += f" = ₸{price * qty}"
                lines.append(line)
            else:
                lines.append(f"• {str(it)}")
    else:
        lines = [f"• {str(items)}"]

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    admin_text = (
        "📦 НОВЫЙ ЗАКАЗ\n"
        f"Время: {now}\n"
        f"От: {user.first_name} (id: {user.id}, {username})\n"
        f"Телефон: {phone or '—'}\n"
        f"Адрес: {address or '—'}\n\n"
        "Состав заказа:\n" + ("\n".join(lines) if lines else "• (пусто)")
    )

    if total is not None:
        admin_text += f"\n\nИТОГО: ₸{total}"

    # Клиенту
    bot.send_message(message.chat.id, "✅ Заказ принят! Мы скоро свяжемся с вами.")

    # Админу + удобная кнопка "написать админу" (опционально)
    bot.send_message(ADMIN_ID, admin_text)

    if ADMIN_USERNAME:
        bot.send_message(
            message.chat.id,
            "Если нужно уточнить детали — напишите администратору:",
            reply_markup=build_inline_contact()
        )


bot.polling(none_stop=True)
