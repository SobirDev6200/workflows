# bot.py
import os
import sys
import logging
import asyncio

from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
import google.generativeai as genai
from dotenv import load_dotenv


# .env fayldan yuklash
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "7274726426:AAHlxzUO3BGIJj0Z8hOypAxu7Anif12JpV0")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyAMcNEDZeeHNdgBTk5tuYZSe6YsmXXfy48")
ADMIN_ID = os.getenv("ADMIN_ID", "6789585626")

# ADMIN_ID ni int ga o'tkazish
try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    raise ValueError("❌ ADMIN_ID raqam formatida bo'lishi kerak!")

if not all([BOT_TOKEN, GEMINI_API_KEY, ADMIN_ID]):
    raise ValueError("❌ Barcha tokenlar va ADMIN_ID .env faylida topilmadi!")


logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Bot va dispatcher
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()
router = Router()
dp.include_router(router)  # ✅ Router ni dispatcherga qo'shish


# Suhbat holatlari
class ChatStates(StatesGroup):
    chatting = State()


# === Gemini AI sozlash ===
try:
    genai.configure(api_key=GEMINI_API_KEY)

    # Modelni to'g'ridan-to'g'ri tanlash
    try:
        gemini_model = genai.GenerativeModel('gemini-2.0-flash')
        logging.info("✅ Gemini AI modeli 'gemini-2.0-flash' muvaffaqiyatli yuklandi.")
    except Exception as model_error:
        logging.warning(f"⚠️ 'gemini-2.0-flash' topilmadi. 'gemini-pro' ishlatilmoqda: {model_error}")
        gemini_model = genai.GenerativeModel('gemini-pro')

except Exception as e:
    logging.error(f"Gemini AI sozlashda xatolik: {e}")
    sys.exit(1)


main_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="AI bilan suhbatlash")]],
    resize_keyboard=True
)

admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Statistika")],
        [KeyboardButton(text="Botni qayta ishga tushirish")],
        [KeyboardButton(text="Asosiy panelga qaytish")]
    ],
    resize_keyboard=True
)


@router.message(CommandStart())
async def command_start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 Salom, admin! Maxsus panelga xush kelibsiz.", reply_markup=admin_keyboard)
    else:
        await message.answer("🤖 Salom! Men sizning AI yordamchingizman.", reply_markup=main_keyboard)


@router.message(lambda message: message.text == "Asosiy panelga qaytish")
async def back_to_main_panel(message: types.Message, state: FSMContext):
    await state.clear()
    if message.from_user.id == ADMIN_ID:
        await message.answer("🏠 Asosiy panel.", reply_markup=main_keyboard)
    else:
        await message.answer("🏠 Asosiy panel.", reply_markup=main_keyboard)


@router.message(lambda message: message.text == "Statistika")
async def show_stats(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        stats_info = "📊 Bot statistikasi:\n- Foydalanuvchilar soni: ...\n- Yuborilgan xabarlar: ..."
        await message.answer(stats_info)
    else:
        await message.answer("⛔ Siz bu buyruqdan foydalana olmaysiz.")


@router.message(lambda message: message.text == "Botni qayta ishga tushirish")
async def restart_bot(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("♻️ Bot qayta ishga tushirilmoqda...")
        os.execv(sys.executable, ['python'] + sys.argv)
    else:
        await message.answer("⛔ Siz bu buyruqdan foydalana olmaysiz.")


@router.message(lambda message: message.text == "AI bilan suhbatlash")
async def start_chat_handler(message: types.Message, state: FSMContext):
    await state.set_state(ChatStates.chatting)
    await message.answer("💬 Suhbatni boshlashingiz mumkin. Tugatish uchun /stop yuboring.")


@router.message(Command('stop'), StateFilter(ChatStates.chatting))
async def handle_stop_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("⛔ Suhbat to'xtatildi. Yana boshlash uchun 'AI bilan suhbatlash' tugmasini bosing.")


@router.message(StateFilter(ChatStates.chatting))
async def process_user_message(message: types.Message):
    if message.text in ["AI bilan suhbatlash", "Statistika", "Botni qayta ishga tushirish", "Asosiy panelga qaytish"]:
        return

    await bot.send_chat_action(message.chat.id, "typing")
    try:
        user_input = message.text
        response = gemini_model.generate_content(user_input)

        # Gemini javobini olish
        text_response = response.text if hasattr(response, "text") else "⚠️ Javobni olishda xatolik."
        
        # Xabar uzunligi tekshirish (Telegram limiti ~4096 belgi)
        if len(text_response) > 4000:
            text_response = text_response[:4000] + "...\n\n⚠️ Javob qisqartirildi"
            
        await message.answer(text_response)

    except Exception as e:
        logging.error(f"Gemini AI bilan xatolik: {e}")
        await message.answer("⚠️ Kechirasiz, hozirda so'rovingizni qayta ishlay olmadim. Keyinroq urinib ko'ring.")


# === Main ===
async def main():
    logging.info("🚀 Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())