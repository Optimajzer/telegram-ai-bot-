import asyncio
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OWNER_ID = int(os.getenv("OWNER_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
client = AsyncOpenAI(api_key=OPENAI_API_KEY)


# =========================
# СЦЕНАРНЫЕ СОСТОЯНИЯ
# =========================

class Scenario(StatesGroup):
    project_name = State()
    niche = State()
    goal = State()
    budget = State()
    contact = State()


# =========================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================

async def save_lead(data: dict):
    with open("leads.txt", "a", encoding="utf-8") as f:
        f.write(
            f"\n--- {datetime.now()} ---\n"
            f"Проект: {data.get('project_name')}\n"
            f"Сфера: {data.get('niche')}\n"
            f"Задача: {data.get('goal')}\n"
            f"Бюджет: {data.get('budget')}\n"
            f"Контакт: {data.get('contact')}\n"
        )


async def ask_ai(message: str):
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты профессиональный консультант по разработке Telegram-ботов "
                    "и AI-решений для бизнеса. Отвечай кратко, по делу, уверенно. "
                    "Без воды, без смайликов, без длинных текстов."
                ),
            },
            {"role": "user", "content": message},
        ],
        temperature=0.7,
    )

    return response.choices[0].message.content


def looks_like_scenario_answer(text: str):
    # простая проверка — короткий конкретный ответ
    if len(text) > 150:
        return False
    if "?" in text:
        return False
    return True


# =========================
# СТАРТ
# =========================

@dp.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    await state.set_state(Scenario.project_name)
    await state.update_data(mode="scenario")

    await message.answer(
        "Здравствуйте.\n\n"
        "Я помогаю предпринимателям создавать Telegram-ботов для бизнеса.\n\n"
        "Ответьте на несколько коротких вопросов, чтобы я понял вашу задачу.\n\n"
        "Как называется ваш проект или компания?"
    )


# =========================
# СЦЕНАРИЙ
# =========================

@dp.message(Scenario.project_name)
async def get_project_name(message: Message, state: FSMContext):
    if not looks_like_scenario_answer(message.text):
        await switch_to_ai(message, state)
        return

    await state.update_data(project_name=message.text)
    await state.set_state(Scenario.niche)

    await message.answer(
        "В какой сфере работает ваш бизнес?"
    )


@dp.message(Scenario.niche)
async def get_niche(message: Message, state: FSMContext):
    if not looks_like_scenario_answer(message.text):
        await switch_to_ai(message, state)
        return

    await state.update_data(niche=message.text)
    await state.set_state(Scenario.goal)

    await message.answer(
        "Какую задачу должен решать бот?"
    )


@dp.message(Scenario.goal)
async def get_goal(message: Message, state: FSMContext):
    if not looks_like_scenario_answer(message.text):
        await switch_to_ai(message, state)
        return

    await state.update_data(goal=message.text)
    await state.set_state(Scenario.budget)

    await message.answer(
        "Планируете ли вы бюджет на разработку? "
        "Можно указать диапазон."
    )


@dp.message(Scenario.budget)
async def get_budget(message: Message, state: FSMContext):
    if not looks_like_scenario_answer(message.text):
        await switch_to_ai(message, state)
        return

    await state.update_data(budget=message.text)
    await state.set_state(Scenario.contact)

    await message.answer(
        "Оставьте контакт для связи (Telegram или номер)."
    )


@dp.message(Scenario.contact)
async def get_contact(message: Message, state: FSMContext):
    if not looks_like_scenario_answer(message.text):
        await switch_to_ai(message, state)
        return

    data = await state.get_data()
    data["contact"] = message.text

    await save_lead(data)
    await state.clear()

    await message.answer(
        "Благодарю.\n\n"
        "Я изучу информацию и свяжусь с вами для обсуждения деталей."
    )


# =========================
# ПЕРЕКЛЮЧЕНИЕ В AI
# =========================

async def switch_to_ai(message: Message, state: FSMContext):
    await state.clear()
    response = await ask_ai(message.text)
    await message.answer(response)


# =========================
# AI РЕЖИМ
# =========================

@dp.message()
async def ai_handler(message: Message):
    response = await ask_ai(message.text)
    await message.answer(response)


# =========================
# ЗАПУСК
# =========================

async def main():
    print("AI-консультант запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())