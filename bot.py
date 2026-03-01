import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ====== USER STATES ======
user_states = {}

# ====== KEYBOARD ======
def main_keyboard():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧠 Консультация")],
            [KeyboardButton(text="💬 Свободный режим")]
        ],
        resize_keyboard=True
    )
    return kb

# ====== START ======
@dp.message(Command("start"))
async def start(message: types.Message):
    user_states[message.from_user.id] = {
        "mode": "consultation",
        "step": "project_name",
        "data": {}
    }

    await message.answer(
        "Здравствуйте.\n\n"
        "Я помогаю предпринимателям внедрять Telegram-ботов для бизнеса.\n\n"
        "Чтобы предложить вам подходящее решение, задам несколько коротких вопросов.\n\n"
        "Как называется ваш проект или компания?",
        reply_markup=main_keyboard()
    )

# ====== MODE SWITCH ======
@dp.message(lambda m: m.text == "🧠 Консультация")
async def consultation_mode(message: types.Message):
    user_states[message.from_user.id] = {
        "mode": "consultation",
        "step": "project_name",
        "data": {}
    }

    await message.answer(
        "Отлично.\n\nНачнём с базовой информации.\n\n"
        "Как называется ваш проект или компания?",
        reply_markup=main_keyboard()
    )

@dp.message(lambda m: m.text == "💬 Свободный режим")
async def free_mode(message: types.Message):
    user_states[message.from_user.id] = {
        "mode": "free"
    }

    await message.answer(
        "Вы в свободном режиме.\n\n"
        "Можете задать любой вопрос.",
        reply_markup=main_keyboard()
    )

# ====== EXIT DETECTION ======
def is_exit_from_scenario(text: str):
    triggers = ["сколько", "цена", "как", "что если", "?"]
    if len(text.split()) > 15:
        return True
    for t in triggers:
        if t in text.lower():
            return True
    return False

# ====== TOXIC FILTER ======
def is_toxic(text: str):
    bad_words = ["иди нах", "пошел", "долбо", "еба", "бля"]
    return any(word in text.lower() for word in bad_words)

# ====== MAIN HANDLER ======
@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text

    # Toxic handling
    if is_toxic(text):
        await message.answer(
            "Давайте общаться конструктивно. Я здесь, чтобы помочь вам."
        )
        return

    state = user_states.get(user_id)

    if not state:
        user_states[user_id] = {"mode": "free"}
        state = user_states[user_id]

    # FREE MODE
    if state.get("mode") == "free":
        response = await ask_ai(text)
        await message.answer(response)
        return

    # CONSULTATION MODE
    if state.get("mode") == "consultation":

        if is_exit_from_scenario(text):
            user_states[user_id]["mode"] = "free"
            await message.answer(
                "Похоже, вы задали отдельный вопрос.\n\n"
                "Перехожу в свободный режим."
            )
            response = await ask_ai(text)
            await message.answer(response)
            return

        step = state.get("step")

        if step == "project_name":
            state["data"]["project_name"] = text
            state["step"] = "sphere"
            await message.answer("В какой сфере работает ваш бизнес?")
            return

        elif step == "sphere":
            state["data"]["sphere"] = text
            state["step"] = "goal"
            await message.answer("Какую задачу должен решать бот?")
            return

        elif step == "goal":
            state["data"]["goal"] = text
            state["mode"] = "free"

            summary = (
                f"Спасибо.\n\n"
                f"Проект: {state['data']['project_name']}\n"
                f"Сфера: {state['data']['sphere']}\n"
                f"Задача: {state['data']['goal']}\n\n"
                f"Я подготовлю оптимальную концепцию решения."
            )

            await message.answer(summary)

            ai_response = await ask_ai(
                f"Предложи профессиональную концепцию Telegram-бота для бизнеса "
                f"{state['data']['project_name']} в сфере {state['data']['sphere']} "
                f"с задачей {state['data']['goal']}."
            )

            await message.answer(ai_response)
            return

# ====== OPENAI ======
async def ask_ai(prompt):
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Ты профессиональный AI-консультант по внедрению Telegram-ботов."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())