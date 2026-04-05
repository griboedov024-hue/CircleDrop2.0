import asyncio
import json
import os
import random
from datetime import datetime
from telethon import TelegramClient, events

# ========== ТВОИ ДАННЫЕ ==========
API_ID = 2040
API_HASH = 'b18441a1ff607e10a989891a5462e627'
BOT_TOKEN = '8652637911:AAE_ksbqSvl_USWUbNrZryVvuu1B1PXd_m4'
# =================================

DATA_FILE = "video_notes_data.json"
USERS_FILE = "users_list.json"
user_videos = {}
users_list = {}

def save_data():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(user_videos, f, ensure_ascii=False, indent=2, default=str)
    print("✅ Данные сохранены")

def load_data():
    global user_videos
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            user_videos = json.load(f)
        print(f"✅ Загружены данные для {len(user_videos)} пользователей")

def save_users():
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users_list, f, ensure_ascii=False, indent=2, default=str)
    print("✅ Список пользователей сохранён")

def load_users():
    global users_list
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users_list = json.load(f)
        print(f"✅ Загружено {len(users_list)} пользователей")

def add_user(user_id, username, first_name):
    user_id = str(user_id)
    if user_id not in users_list:
        users_list[user_id] = {
            "username": username,
            "first_name": first_name,
            "first_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_users()
        print(f"📌 Новый пользователь: @{username} ({first_name}) ID: {user_id}")
    else:
        users_list[user_id]["last_seen"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_users()

def print_users_to_console():
    """Выводит список всех пользователей в консоль"""
    print("\n" + "="*50)
    print("📋 СПИСОК ВСЕХ ПОЛЬЗОВАТЕЛЕЙ БОТА")
    print("="*50)
    if not users_list:
        print("Пользователей пока нет")
    else:
        for uid, info in users_list.items():
            username = info.get('username', 'нет')
            name = info.get('first_name', 'неизвестно')
            has_video = "✅" if uid in user_videos and user_videos[uid] else "❌"
            print(f"{has_video} 🆔 {uid} | @{username} | {name}")
    print("="*50 + "\n")

def get_random_user(exclude_user_id):
    """Возвращает случайного пользователя из списка (исключая текущего)"""
    exclude_id = str(exclude_user_id)
    # Берём ВСЕХ пользователей, кроме отправителя
    potential_users = [uid for uid in users_list.keys() if uid != exclude_id]
    
    if not potential_users:
        return None
    
    random_id = random.choice(potential_users)
    return {
        "id": random_id,
        "username": users_list[random_id].get("username", "неизвестно"),
        "first_name": users_list[random_id].get("first_name", "пользователь")
    }

bot = TelegramClient('bot_session', API_ID, API_HASH)

async def main():
    load_data()
    load_users()
    await bot.start(bot_token=BOT_TOKEN)
    
    # Выводим список пользователей при запуске
    print_users_to_console()
    
    print("🎬 Бот запущен!")
    
    @bot.on(events.NewMessage(pattern='/start'))
    async def start(event):
        user_id = event.sender_id
        username = event.sender.username or "нет"
        first_name = event.sender.first_name or "неизвестно"
        add_user(user_id, username, first_name)
        print_users_to_console()  # Обновляем вывод
        
        await event.reply(
            "🎬 *БОТ ДЛЯ ПЕРЕСЫЛКИ КРУЖКОВ*\n\n"
            "📹 Отправь кружок — я сохраню\n"
            "📤 /s @username — отправить последний\n"
            "📋 /list — список кружков\n"
            "🎲 /random — отправить кружок случайному пользователю\n\n"
            f"👥 Всего пользователей: {len(users_list)}",
            parse_mode='markdown'
        )
    
    @bot.on(events.NewMessage(pattern='/list'))
    async def list_videos(event):
        user_id = str(event.sender_id)
        if user_id not in user_videos or not user_videos[user_id]:
            await event.reply("📭 Нет кружков")
            return
        videos = user_videos[user_id]
        msg = f"📋 *ТВОИ КРУЖКИ* ({len(videos)}/10)\n\n"
        for i, v in enumerate(videos[-5:], 1):
            msg += f"{i}. 📅 {v['date']} | ⏱️ {v['duration']} сек\n"
        await event.reply(msg, parse_mode='markdown')
    
    @bot.on(events.NewMessage(pattern='/s (.+)'))
    async def send_video(event):
        user_id = str(event.sender_id)
        target = event.pattern_match.group(1).strip()
        if target.startswith('@'):
            target = target[1:]

        if user_id not in user_videos or not user_videos[user_id]:
            await event.reply("❌ Нет кружков")
            return

        video = user_videos[user_id][-1]
        msg_id = video.get('message_id')
        chat_id = video.get('chat_id')

        if not msg_id or not chat_id:
            await event.reply("❌ Ошибка")
            return

        original = await bot.get_messages(int(chat_id), ids=int(msg_id))
        if original and original.video_note:
            try:
                await bot.send_file(target, original.video_note, video_note=True)
                await event.reply(f"✅ Отправлено @{target}")
            except Exception as e:
                await event.reply(f"⚠️ Ошибка: получатель не писал боту или username неверный")
    
    @bot.on(events.NewMessage(pattern='/random'))
    async def random_send(event):
        sender_id = str(event.sender_id)
        sender_username = event.sender.username or "неизвестно"
        
        # Проверяем, есть ли у отправителя кружки
        if sender_id not in user_videos or not user_videos[sender_id]:
            await event.reply(
                "❌ *У тебя нет сохранённых кружков*\n\n"
                "Сначала отправь мне кружок, а потом используй /random",
                parse_mode='markdown'
            )
            return
        
        # Проверяем, есть ли другие пользователи
        if len(users_list) <= 1:
            await event.reply(
                "❌ *Нет других пользователей*\n\n"
                "Попроси друзей написать боту /start, тогда сможете обмениваться кружками!\n"
                f"📊 Сейчас в боте только ты (и {len(users_list)} пользователей)",
                parse_mode='markdown'
            )
            return
        
        # Выбираем случайного получателя (НЕ ТОЛЬКО С КРУЖКАМИ, А ЛЮБОГО)
        random_user = get_random_user(sender_id)
        
        if not random_user:
            await event.reply(
                "❌ *Нет других пользователей*\n\n"
                "Попроси друзей написать боту /start",
                parse_mode='markdown'
            )
            return
        
        target_id = random_user["id"]
        target_username = random_user["username"]
        
        # Берём последний кружок отправителя
        video = user_videos[sender_id][-1]
        msg_id = video.get('message_id')
        chat_id = video.get('chat_id')
        
        if not msg_id or not chat_id:
            await event.reply("❌ Ошибка при отправке")
            return
        
        original = await bot.get_messages(int(chat_id), ids=int(msg_id))
        if original and original.video_note:
            try:
                # Отправляем кружок случайному пользователю
                await bot.send_file(target_id, original.video_note, video_note=True)
                
                await event.reply(
                    f"🎲 *КРУЖОК ОТПРАВЛЕН!*\n\n"
                    f"📤 Получатель: @{target_username}\n"
                    f"👥 Всего пользователей в боте: {len(users_list)}\n\n"
                    f"💡 Хочешь отправить ещё? Напиши /random",
                    parse_mode='markdown'
                )
                
                # Пробуем уведомить получателя
                try:
                    await bot.send_message(
                        target_id,
                        f"🎉 *Тебе отправили кружок!*\n\n"
                        f"👤 Отправитель: @{sender_username}\n"
                        f"📹 Проверь свой чат, кружок уже у тебя!\n\n"
                        f"💡 Чтобы ответить тем же, отправь свой кружок и напиши /random",
                        parse_mode='markdown'
                    )
                except Exception as notify_error:
                    print(f"Не удалось уведомить получателя: {notify_error}")
                    
            except Exception as e:
                await event.reply(f"⚠️ Ошибка при отправке: {str(e)[:100]}")
        else:
            await event.reply("❌ Ошибка: не удалось найти кружок")
    
    @bot.on(events.NewMessage)
    async def save_video(event):
        if not event.message.video_note:
            return
        
        user_id = str(event.sender_id)
        username = event.sender.username or "нет"
        first_name = event.sender.first_name or "неизвестно"
        
        add_user(user_id, username, first_name)
        print_users_to_console()  # Обновляем вывод
        
        vn = event.message.video_note

        if user_id not in user_videos:
            user_videos[user_id] = []

        user_videos[user_id].append({
            "message_id": event.message.id,
            "chat_id": event.chat_id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "duration": vn.duration if hasattr(vn, 'duration') else 0
        })

        if len(user_videos[user_id]) > 10:
            user_videos[user_id] = user_videos[user_id][-10:]

        save_data()
        await event.reply(
            f"✅ *Кружок сохранён!* ({len(user_videos[user_id])}/10)\n\n"
            f"🎲 /random — отправить кружок случайному пользователю\n"
            f"👥 Всего пользователей в боте: {len(users_list)}",
            parse_mode='markdown'
        )

    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())