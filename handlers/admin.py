from aiogram import Router, F, types
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ADMIN_ID, COURIER_ID
from utils.database import get_orders_by_status, update_order_status, get_order_user_id

router = Router()


class AdminAction(CallbackData, prefix="adm"):
    action: str
    order_id: int


@router.message(F.text == "📊 Все заказы (Админ)")
async def admin_orders(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    orders = get_orders_by_status()
    if not orders:
        await message.answer("Активных заказов нет. 📭")
        return

    for row in orders:
        oid, details, status = row["id"], row["details"], row["status"]
        kb = InlineKeyboardBuilder()

        if status == "В обработке":
            kb.button(text="✅ Подтвердить",
                      callback_data=AdminAction(action="confirm", order_id=oid).pack())
            kb.button(text="❌ Отменить",
                      callback_data=AdminAction(action="cancel", order_id=oid).pack())
        elif status == "Подтвержден":
            kb.button(text="🛵 Передать курьеру",
                      callback_data=AdminAction(action="tocur", order_id=oid).pack())

        kb.adjust(1)
        await message.answer(
            f"📦 <b>Заказ №{oid}</b>\n"
            f"Статус: <code>{status}</code>\n"
            f"Состав:\n{details}",
            reply_markup=kb.as_markup()
        )


@router.callback_query(AdminAction.filter())
async def handle_decisions(callback: types.CallbackQuery, callback_data: AdminAction):
    await callback.answer()

    bot = callback.bot
    action = callback_data.action
    order_id = callback_data.order_id
    user_id = get_order_user_id(order_id)
    text = callback.message.text or ""

    if action == "confirm":
        update_order_status(order_id, "Подтвержден")
        await bot.send_message(user_id, f"🥳 Заказ №{order_id} подтвержден! Начинаем готовить.")
        kb = InlineKeyboardBuilder()
        kb.button(text="🛵 Передать курьеру",
                  callback_data=AdminAction(action="tocur", order_id=order_id).pack())
        await callback.message.edit_text(
            f"{text}\n\n✅ Статус: Подтвержден",
            reply_markup=kb.as_markup()
        )

    elif action == "cancel":
        update_order_status(order_id, "Отменен")
        await bot.send_message(user_id, f"😔 Заказ №{order_id} отменен администратором.")
        await callback.message.edit_text(f"{text}\n\n❌ Статус: Отменен")

    elif action == "tocur":
        update_order_status(order_id, "В пути")
        await bot.send_message(user_id, f"🛵 Ваш заказ №{order_id} уже в пути!")

        if not COURIER_ID:
            await callback.message.answer("⚠️ Ошибка: ID курьера не указан!")
            return

        kb_cur = InlineKeyboardBuilder()
        kb_cur.button(text="✅ Доставлено",
                      callback_data=AdminAction(action="done", order_id=order_id).pack())
        await bot.send_message(
            COURIER_ID,
            f"📦 <b>ЗАКАЗ НА ДОСТАВКУ №{order_id}</b>\n{text}",
            reply_markup=kb_cur.as_markup()
        )
        await callback.message.edit_text(f"{text}\n\n🚚 Статус: У курьера")

    elif action == "done":
        update_order_status(order_id, "Доставлен")
        await bot.send_message(user_id, f"🍕 Заказ №{order_id} доставлен! Приятного аппетита!")
        await bot.send_message(ADMIN_ID, f"🏁 Заказ №{order_id} успешно доставлен курьером.")
        await callback.message.edit_text(f"{text}\n\n🏁 Статус: ДОСТАВЛЕН")
