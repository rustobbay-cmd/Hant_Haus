from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from config import ADMIN_ID, COURIER_ID


def main_menu_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="📖 Меню")
    builder.button(text="🛒 Корзина")
    builder.button(text="⏳ Мои заказы")
    builder.adjust(2)

    if user_id == ADMIN_ID:
        builder.row(KeyboardButton(text="📊 Все заказы (Админ)"))

    if COURIER_ID and user_id == COURIER_ID and user_id != ADMIN_ID:
        builder.row(KeyboardButton(text="🛵 Заказы на доставку"))

    return builder.as_markup(resize_keyboard=True)
