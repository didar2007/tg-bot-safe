import os
import json
from datetime import datetime

import telebot
from telebot import types


def must_get_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Переменная окружения {name} не задана. "
                           f"Добавь её в Railway → Variables.")
    return value


# === Настройки только через переменные окружения (Railway Variables) ===
TOKEN = must_get_env("TOKEN")
WEBAPP_URL = must_get_env("WEBAPP_URL")
ADMIN_ID = int(must_get_env("ADMIN_ID"))

bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=["start"])
def start(message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    webapp_btn = types.KeyboardButton(
        "🛒 Открыть магазин",
        web_app=types.WebAppInfo(url=WEBAPP_URL),
    )
    kb.add(webapp_btn)

    bot.send_message(
        message.chat.id,
        "Нажми кнопку ниже, чтобы открыть магазин:",
        reply_markup=kb
    )


@bot.message_handler(commands=["myid"])
def myid(message):
    bot.send_message(message.chat.id, f"Твой ID: {message.from_user.id}")


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

    # Если пришёл не JSON — отправим админу как есть (на всякий случай)
    if not isinstance(payload, dict):
        bot.send_message(message.chat.id, "✅ Заказ принят!")
        bot.send_message(
            ADMIN_ID,
            "📦 НОВЫЙ ЗАКАЗ (сырой текст)\n"
            f"От: {user.first_name} (id: {user.id}, {username})\n\n"
            f"{raw}"
        )
        return

    # Ожидаем новый формат от Mini App:
    # {
    #   "type": "order",
    #   "address": "...",
    #   "items": [{title, model, flavor, price, qty}, ...],
    #   "total": 12345
    # }

    address = (payload.get("address") or "").strip()
    phone = (payload.get("phone") or "").strip()
    comment = (payload.get("comment") or "").strip()
    items = payload.get("items") or []
    total = payload.get("total", None)

    lines = []
    if isinstance(items, list):
        for it in items:
            if isinstance(it, dict):
                title = it.get("title", "")
                model = it.get("model", "")
                flavor = it.get("flavor", "")
                qty = it.get("qty", 1)
                price = it.get("price", 0)

                # строка товара
                line = f"• {title} {model} — {flavor} ×{qty}"
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
        f"Адрес: {address or '—'}\n"
        f"Комментарий: {comment or '—'}\n\n"
        "Состав заказа:\n" + ("\n".join(lines) if lines else "• (пусто)")
    )

    if total is not None:
        admin_text += f"\n\nИТОГО: ₸{total}"

    # Клиенту
    bot.send_message(message.chat.id, "✅ Заказ принят! Мы скоро свяжемся с вами.")

    # Админу
    bot.send_message(ADMIN_ID, admin_text)


bot.polling(none_stop=True)
