from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from config import MENU, MENU_INDEX, ADMIN_ID
from handlers.admin import AdminAction
import keyboards.reply as kb_reply

router = Router()


class MenuCat(CallbackData, prefix="cat"):
    idx: int


class MenuAdd(CallbackData, prefix="add"):
    item_id: int


class CartAction(CallbackData, prefix="cart"):
    action: str
    item_id: int = -1


class OrderState(StatesGroup):
    waiting_method  = State()
    waiting_address = State()
    waiting_phone   = State()
    waiting_payment = State()


def get_item_price(item_name: str) -> int:
    for cat in MENU.values():
        if item_name in cat:
            return cat[item_name]
    return 0


def get_item_id(item_name: str) -> int:
    for item_id, (_, name) in MENU_INDEX.items():
        if name == item_name:
            return item_id
    return -1


def get_categories_keyboard():
    builder = InlineKeyboardBuilder()
    for idx, cat in enumerate(MENU.keys()):
        builder.button(text=cat, callback_data=MenuCat(idx=idx).pack())
    builder.adjust(2)
    return builder.as_markup()


def get_menu_keyboard(category: str):
    builder = InlineKeyboardBuilder()
    for item_id, (cat, item_name) in MENU_INDEX.items():
        if cat == category:
            price = MENU[category][item_name]
            builder.row(types.InlineKeyboardButton(
                text=f"{item_name} — {price}₽",
                callback_data=MenuAdd(item_id=item_id).pack()
            ))
    builder.row(types.InlineKeyboardButton(
        text="⬅️ Назад к категориям",
        callback_data="back_to_cats"
    ))
    return builder.as_markup()


def get_cart_keyboard(user_id: int):
    from utils.database import get_cart_db
    items = get_cart_db(user_id)
    if not items:
        return None

    builder = InlineKeyboardBuilder()
    total_sum = 0

    for row in items:
        item_name, count = row["item"], row["count"]
        price = get_item_price(item_name)
        subtotal = price * count
        total_sum += subtotal
        item_id = get_item_id(item_name)

        builder.row(types.InlineKeyboardButton(
            text=f"🔹 {item_name} ({subtotal}₽)",
            callback_data=CartAction(action="none", item_id=-1).pack()
        ))
        builder.row(
            types.InlineKeyboardButton(
                text="➖",
                callback_data=CartAction(action="sub", item_id=item_id).pack()
            ),
            types.InlineKeyboardButton(
                text=f"{count} шт.",
                callback_data=CartAction(action="none", item_id=-1).pack()
            ),
            types.InlineKeyboardButton(
                text="➕",
                callback_data=CartAction(action="add", item_id=item_id).pack()
            ),
        )

    builder.row(types.InlineKeyboardButton(
        text=f"💰 Оформить заказ: {total_sum}₽",
        callback_data=CartAction(action="checkout", item_id=-1).pack()
    ))
    builder.row(types.InlineKeyboardButton(
        text="🗑 Очистить корзину",
        callback_data=CartAction(action="clear", item_id=-1).pack()
    ))
    return builder.as_markup()


@router.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Добро пожаловать в <b>ХАНТ ХАУС</b>!",
        reply_markup=kb_reply.main_menu_keyboard(message.from_user.id)
    )


@router.message(F.text == "📖 Меню")
async def show_categories(message: types.Message):
    await message.answer("Выберите категорию:", reply_markup=get_categories_keyboard())


@router.callback_query(MenuCat.filter())
async def show_items(callback: types.CallbackQuery, callback_data: MenuCat):
    await callback.answer()
    cat = list(MENU.keys())[callback_data.idx]
    await callback.message.edit_text(
        f"🍴 Раздел: {cat}",
        reply_markup=get_menu_keyboard(cat)
    )


@router.callback_query(F.data == "back_to_cats")
async def back_to_cats(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "Выберите категорию:",
        reply_markup=get_categories_keyboard()
    )


@router.callback_query(MenuAdd.filter())
async def add_to_cart(callback: types.CallbackQuery, callback_data: MenuAdd):
    from utils.database import add_to_cart_db
    _, item_name = MENU_INDEX[callback_data.item_id]
    add_to_cart_db(callback.from_user.id, item_name)
    await callback.answer(f"✅ {item_name} добавлен в корзину!")


@router.message(F.text == "🛒 Корзина")
async def show_cart(message: types.Message):
    kb = get_cart_keyboard(message.from_user.id)
    if kb:
        await message.answer("🛒 <b>Ваша корзина:</b>", reply_markup=kb)
    else:
        await message.answer("Ваша корзина пуста 🛒\nВыберите что-нибудь в меню!")


@router.callback_query(CartAction.filter(F.action == "checkout"))
async def checkout(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    builder = ReplyKeyboardBuilder()
    builder.button(text="🚚 Доставка")
    builder.button(text="🥡 Самовывоз")
    await callback.message.delete()
    await callback.bot.send_message(
        callback.from_user.id,
        "Выберите способ получения:",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )
    await state.set_state(OrderState.waiting_method)


@router.callback_query(CartAction.filter())
async def cart_handler(callback: types.CallbackQuery, callback_data: CartAction):
    from utils.database import add_to_cart_db, remove_from_cart_db, clear_cart_db
    await callback.answer()

    action = callback_data.action
    item_id = callback_data.item_id
    uid = callback.from_user.id

    if action == "none":
        return
    elif action == "add":
        _, item_name = MENU_INDEX[item_id]
        add_to_cart_db(uid, item_name)
        await callback.message.edit_reply_markup(reply_markup=get_cart_keyboard(uid))
    elif action == "sub":
        _, item_name = MENU_INDEX[item_id]
        remove_from_cart_db(uid, item_name)
        kb = get_cart_keyboard(uid)
        if kb:
            await callback.message.edit_reply_markup(reply_markup=kb)
        else:
            await callback.message.edit_text("Корзина пуста 🛒")
    elif action == "clear":
        clear_cart_db(uid)
        await callback.message.edit_text("Корзина очищена 🗑")


@router.message(OrderState.waiting_method)
async def method_chosen(message: types.Message, state: FSMContext):
    await state.update_data(method=message.text)
    if "Доставка" in message.text:
        await message.answer("Введите адрес доставки:")
        await state.set_state(OrderState.waiting_address)
    else:
        await state.update_data(address="Самовывоз")
        builder = ReplyKeyboardBuilder()
        builder.button(text="📱 Отправить номер", request_contact=True)
        await message.answer(
            "Нажмите кнопку ниже, чтобы передать телефон:",
            reply_markup=builder.as_markup(resize_keyboard=True)
        )
        await state.set_state(OrderState.waiting_phone)


@router.message(OrderState.waiting_address)
async def ask_phone(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    builder = ReplyKeyboardBuilder()
    builder.button(text="📱 Отправить номер", request_contact=True)
    await message.answer(
        "Ваш номер телефона:",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )
    await state.set_state(OrderState.waiting_phone)


@router.message(OrderState.waiting_phone, F.content_type.in_({"contact", "text"}))
async def ask_payment(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone)
    builder = ReplyKeyboardBuilder()
    builder.button(text="💵 Наличными")
    builder.button(text="💳 Картой")
    await message.answer(
        "Способ оплаты:",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )
    await state.set_state(OrderState.waiting_payment)


@router.message(OrderState.waiting_payment)
async def finalize(message: types.Message, state: FSMContext):
    from utils.database import add_order_to_db, get_cart_db, clear_cart_db

    data = await state.get_data()
    items = get_cart_db(message.from_user.id)

    total_price = 0
    details_list = []
    for row in items:
        name, count = row["item"], row["count"]
        price = get_item_price(name)
        sub = price * count
        total_price += sub
        details_list.append(f"• {name} x{count} ({sub}₽)")

    details_text = "\n".join(details_list)

    oid = add_order_to_db(
        message.from_user.id,
        f"{details_text}\nИТОГО: {total_price}₽",
        data["method"],
        data["address"],
        data["phone"],
        message.from_user.full_name
    )

    adm_kb = InlineKeyboardBuilder()
    adm_kb.button(text="✅ Подтвердить",
                  callback_data=AdminAction(action="confirm", order_id=oid).pack())
    adm_kb.button(text="❌ Отменить",
                  callback_data=AdminAction(action="cancel", order_id=oid).pack())
    adm_kb.adjust(2)

    await message.bot.send_message(
        ADMIN_ID,
        f"🔔 <b>НОВЫЙ ЗАКАЗ №{oid}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{details_text}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 <b>ИТОГО: {total_price}₽</b>\n\n"
        f"📍 {data['method']} | 💳 {message.text}\n"
        f"🏠 {data['address']}\n"
        f"📞 {data['phone']}\n"
        f"👤 {message.from_user.full_name}",
        reply_markup=adm_kb.as_markup()
    )

    await message.answer(
        f"✨ Заказ №{oid} на сумму <b>{total_price}₽</b> принят!\n"
        f"Ожидайте подтверждения. 🙏",
        reply_markup=kb_reply.main_menu_keyboard(message.from_user.id)
    )
    clear_cart_db(message.from_user.id)
    await state.clear()


@router.message(F.text == "⏳ Мои заказы")
async def my_orders(message: types.Message):
    from utils.database import get_orders_by_status
    orders = get_orders_by_status(user_id=message.from_user.id)
    if not orders:
        await message.answer("У вас пока нет заказов. 📭")
        return
    for row in orders:
        await message.answer(
            f"📦 <b>Заказ №{row['id']}</b>\n"
            f"Статус: <code>{row['status']}</code>\n"
            f"{row['details']}"
        )
