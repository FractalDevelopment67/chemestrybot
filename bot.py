import telebot
import json
import random
import threading
import hashlib
import uuid
from datetime import datetime
from telebot import types
from datetime import date

TOKEN = "8410255007:AAFK2ySE5yxtaB7Mc6CJBDuESbNTBl-7oZE"
ADMIN_CODE = "5214886769"

bot = telebot.TeleBot(TOKEN)

# ========= DATA =========
elements = json.load(open("elements.json", encoding="utf-8"))

try:
    users = json.load(open("users.json", encoding="utf-8"))
except:
    users = {}

single_games = {}
learn_mode = set()
mp_queue = {}
mp_matches = {}
private_matches = {}
admins = set()
rename_mode = set()
admin_give_mode = {}

# ========= HELPERS =========
def save_users():
    json.dump(users, open("users.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

def season():
    return datetime.now().strftime("%Y-%m")

def hash_pwd(p):
    return hashlib.sha256(p.encode()).hexdigest()

def get_user(uid):
    uid = str(uid)

    if uid not in users:
        users[uid] = {}

    u = users[uid]

    u.setdefault("name", f"User{uid[-4:]}")
    u.setdefault("score", 0)
    u.setdefault("wins", 0)
    u.setdefault("games", 0)
    u.setdefault("season_scores", {})
    u.setdefault("achievements", [])
    u.setdefault("custom_achievements", [])
    u.setdefault("learned_elements", [])

    # 🔥 НОВОЕ
    u.setdefault("day_streak", 0)
    u.setdefault("last_login", None)

    save_users()
    return u

def handle_daily_login(uid):
    u = get_user(uid)
    today = date.today().isoformat()
    yesterday = (date.today().fromordinal(date.today().toordinal() - 1)).isoformat()

    if u["last_login"] == today:
        return  # уже заходил сегодня

    if u["last_login"] == yesterday:
        u["day_streak"] += 1
    else:
        u["day_streak"] = 1

    # 🎁 БОНУС (можешь менять формулу)
    bonus = min(5, u["day_streak"])  # макс 5 очков
    u["score"] += bonus

    u["last_login"] = today
    save_users()

    bot.send_message(
        int(uid),
        f"🔥 *Дейли вход!*\n"
        f"📆 Стрик: {u['day_streak']} дней\n"
        f"🎁 Бонус: +{bonus}⭐",
        parse_mode="Markdown"
    )

def element_of_the_day():
    today = date.today().isoformat()
    random.seed(today)  # ❗ ключевая магия
    return random.choice(elements)

@bot.message_handler(func=lambda m: m.text == "🧪 Элемент дня")
def send_element_of_day(msg):
    try:
        e = element_of_the_day()

        text = (
            f"🧪 *Элемент дня*\n\n"
            f"*{e['ru_name']}* ({e['symbol']})\n"
            f"🔢 Номер: {e['number']}\n"
            f"⚛ Масса: {e.get('atomic_mass','—')}\n"
            f"📦 Группа: {e.get('group','—')}\n"
            f"📐 Период: {e.get('period','—')}\n"
            f"🔗 Валентность: {e.get('valency','—')}\n"
            f"🧩 Тип: {e.get('type','—')}"
        )

        bot.send_message(
            msg.chat.id,
            text,
            parse_mode="Markdown",
            reply_markup=main_menu()
        )

    except Exception as ex:
        bot.send_message(
            msg.chat.id,
            f"❌ Ошибка элемента дня:\n{ex}"
        )

ACHIEVEMENTS = {
    "first_game": {
        "name": "🎯 Первый шаг",
        "desc": "Сыграть первую игру",
        "hidden": False,
        "goal": 1,
        "type": "games"
    },
    "five_games": {
        "name": "🧪 Начинающий химик",
        "desc": "Сыграть 5 игр",
        "hidden": False,
        "goal": 5,
        "type": "games"
    },
    "ten_wins": {
        "name": "🧠 Юный химик",
        "desc": "Выиграть 10 игр",
        "hidden": False,
        "goal": 10,
        "type": "wins"
    },

    "PROFESSOR": {
        "name": "🥼Профессор",
        "desc": "Выиграть 25 игр",
        "hidden": False,
        "goal": 25,
        "type": "wins"
    },

    "mendelevium": {
        "name": "🧬Менделеев",
        "desc": "Изучтить элемент Менделеевий",
        "hidden": True,
        "goal": 1,
        "type": "element_mendelevium"
    },

    "iron":  {
        "name": "🎮Фееерум",
        "desc": "Изучить Железо",
        "hidden": True,
        "goal": 1,
        "type": "element_iron"
    },

    "MEGAKNIGHT": {
        "name": "👑 MEGAKNIGHT",
        "desc": "Выиграть 50 игр",
        "hidden": True,  # 👈 СКРЫТОЕ
        "goal": 50,
        "type": "wins",
        "reward": 3
    },

    "streak_3": {
        "name": "🔥 На огоньке",
        "desc": "Зайти 3 дня подряд",
        "hidden": False,
        "goal": 3,
        "type": "streak"
    },
    "streak_7": {
        "name": "🔥🔥 Горю!",
        "desc": "Зайти 7 дней подряд",
        "hidden": False,
        "goal": 7,
        "type": "streak"
    },
    "streak_30": {
        "name": "Цыпленок жареный",
        "desc": "Зайти 30 дней подряд!1!1",
        "hidden": True,
        "goal": 30,
        "type": "streak"
    }
}

def check_element_achievements(uid, symbol):
    u = get_user(uid)

    mapping = {
        "md": "mendelevium",  # Менделеевий
        "fe": "iron"          # Железо
    }

    if symbol not in mapping:
        return

    key = mapping[symbol]

    if key not in u["achievements"]:
        u["achievements"].append(key)
        save_users()

        bot.send_message(
            int(uid),
            f"🏅 *Новое достижение!*\n{ACHIEVEMENTS[key]['name']}",
            parse_mode="Markdown"
        )

def find_element(query):
    q = query.lower().strip()
    for e in elements:
        if (
            str(e["number"]) == q
            or e["ru_name"].lower() == q
            or e["en_name"].lower() == q
            or e["symbol"].lower() == q
        ):
            return e
    return None

# ========= KEYBOARDS =========
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📸 Фото таблицы", "📘 Выучить элемент")
    kb.row("🧪 Одиночная игра", "👥 Мультиплеер")
    kb.row("🔐 Приватный матч", "🏆 Рейтинг")
    kb.row("📊 Статистика", "🛠Сменить имя")
    kb.row("🏅 Достижения", "ℹ️ Помощь")
#    kb.row("💊 Элемент дня")
    return kb

def rating_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("📅 Сезонный", callback_data="top_season"),
        types.InlineKeyboardButton("🌍 Глобальный", callback_data="top_all")
    )
    return kb

def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🎁 Выдать достижение")
    kb.row("⬅ Назад")
    return kb

def private_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("➕ Создать", callback_data="pm_create"),
        types.InlineKeyboardButton("🔑 Войти", callback_data="pm_join")
    )
    return kb

# ========= START =========
@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id
    get_user(uid)

    handle_daily_login(uid)  # ← ВОТ ЗДЕСЬ

    bot.send_message(
        msg.chat.id,
        "👋 Добро пожаловать!",
        reply_markup=main_menu()
    )

# ========= FOTO =========
@bot.message_handler(func=lambda m: m.text == "📸 Фото таблицы")
def send_table(msg):
    try:
        with open("pt.png", "rb") as p:
            bot.send_photo(msg.chat.id, p, caption="📊 Таблица Менделеева")
    except:
        bot.send_message(msg.chat.id, "❌ Файл pt.png не найден")

# ========= LEARN =========
@bot.message_handler(func=lambda m: m.text == "📘 Выучить элемент")
def learn_start(msg):
    learn_mode.add(msg.chat.id)
    bot.send_message(
        msg.chat.id,
        "Введите номер, название или символ элемента\nПример: 8 / Кислород / O"
    )

@bot.message_handler(func=lambda m: m.chat.id in learn_mode)
def learn_element(msg):
    learn_mode.discard(msg.chat.id)

    e = find_element(msg.text)
    if not e:
        bot.send_message(msg.chat.id, "❌ Элемент не найден", reply_markup=main_menu())
        return

    text = (
        f"🧪 *{e['ru_name']}* ({e['symbol']})\n\n"
        f"🔢 Номер: {e['number']}\n"
        f"⚛ Атомная масса: {e.get('atomic_mass','—')}\n"
        f"📦 Группа: {e.get('group','—')}\n"
        f"📐 Период: {e.get('period','—')}\n"
        f"🔗 Валентность: {e.get('valency','—')}\n"
        f"🧩 Тип: {e.get('type','—')}"
    )

    symbol = e["symbol"].lower()
    u = get_user(msg.from_user.id)

    if symbol not in u["learned_elements"]:
        u["learned_elements"].append(symbol)

    save_users()

    check_element_achievements(msg.from_user.id, symbol)

    bot.send_message(msg.chat.id, text, parse_mode="Markdown", reply_markup=main_menu())

# ========= SINGLE =========
@bot.message_handler(func=lambda m: m.text == "🧪 Одиночная игра")
def single_game(msg):
    e = random.choice(elements)
    single_games[msg.chat.id] = str(e["number"])
    bot.send_message(msg.chat.id, f"Какой номер у {e['ru_name']}?")

@bot.message_handler(func=lambda m: m.chat.id in single_games)
def single_answer(msg):
    uid = msg.from_user.id
    u = get_user(uid)

    u["games"] += 1

    if msg.text.strip() == single_games[msg.chat.id]:
        u["wins"] += 1
        u["score"] += 1
        u["season_scores"][season()] = u["season_scores"].get(season(), 0) + 1
        bot.send_message(msg.chat.id, "✅ Верно!")
    else:
        bot.send_message(msg.chat.id, "❌ Неверно")

    save_users()

    # 🏅 ВОТ ОНО — ДОСТИЖЕНИЯ
    check_achievements(uid)

    del single_games[msg.chat.id]

# ========= MULTI =========
@bot.message_handler(func=lambda m: m.text == "👥 Мультиплеер")
def multiplayer(msg):
    uid = str(msg.from_user.id)

    for other in list(mp_queue):
        mp_queue[other].cancel()
        mp_queue.pop(other)
        start_match(uid, other)
        return

    timer = threading.Timer(10, lambda: start_bot_match(uid))
    mp_queue[uid] = timer
    timer.start()
    bot.send_message(msg.chat.id, "⏳ Поиск соперника...")

def start_match(u1, u2):
    mid = str(uuid.uuid4())
    mp_matches[mid] = {
        "players": [u1, u2],
        "round": 1,
        "scores": {u1: 0, u2: 0},
        "answer": None,
        "bot": False
    }
    start_round(mid)

def start_bot_match(uid):
    mp_queue.pop(uid, None)
    mid = str(uuid.uuid4())
    mp_matches[mid] = {
        "players": [uid, "BOT"],
        "round": 1,
        "scores": {uid: 0, "BOT": 0},
        "answer": None,
        "bot": True
    }
    start_round(mid)

def start_round(mid):
    match = mp_matches[mid]
    e = random.choice(elements)
    match["answer"] = str(e["number"])

    for p in match["players"]:
        if p != "BOT":
            bot.send_message(
                int(p),
                f"🎮 Раунд {match['round']}/3\nКакой номер у {e['ru_name']}?"
            )

@bot.message_handler(func=lambda m: any(str(m.from_user.id) in d["players"] for d in mp_matches.values()))
def mp_answer(msg):
    uid = str(msg.from_user.id)

    for mid, match in list(mp_matches.items()):
        if uid in match["players"]:
            if msg.text.strip() == match["answer"]:
                match["scores"][uid] += 1

            if match["bot"]:
                match["scores"]["BOT"] += random.choice([0, 1])

            match["round"] += 1
            if match["round"] > 3:
                finish_match(mid)
            else:
                start_round(mid)
            return

def finish_match(mid):
    match = mp_matches[mid]
    players = match["players"]
    scores = match["scores"]

    for p in players:
        if p != "BOT":
            u = get_user(p)
            u["games"] += 1

            if scores[p] == max(scores.values()):
                u["wins"] += 1
                u["score"] += 5
                u["season_scores"][season()] = u["season_scores"].get(season(), 0) + 5
                bot.send_message(int(p), "🏆 Победа!")
            else:
                bot.send_message(int(p), "😢 Поражение")

            # 🏅 ВОТ ОНО — ДОСТИЖЕНИЯ
            save_users()
            check_achievements(p)

    del mp_matches[mid]

# ========= PRIVATE =========
@bot.message_handler(func=lambda m: m.text == "🔐 Приватный матч")
def private_menu_handler(msg):
    bot.send_message(msg.chat.id, "Приватный матч:", reply_markup=private_menu())

@bot.callback_query_handler(func=lambda c: c.data == "pm_create")
def pm_create(call):
    code = str(random.randint(100000, 999999))
    mid = str(uuid.uuid4())

    private_matches[code] = mid
    mp_matches[mid] = {
        "players": [str(call.from_user.id)],
        "round": 1,
        "scores": {str(call.from_user.id): 0},
        "answer": None,
        "bot": False
    }

    bot.send_message(call.message.chat.id, f"🔐 Код матча: {code}")

@bot.callback_query_handler(func=lambda c: c.data == "pm_join")
def pm_join(call):
    bot.send_message(call.message.chat.id, "Введите код матча:")
    bot.register_next_step_handler(call.message, pm_join_code)

def pm_join_code(msg):
    code = msg.text.strip()

    if code not in private_matches:
        bot.send_message(msg.chat.id, "❌ Матч не найден")
        return

    mid = private_matches.pop(code)

    mp_matches[mid]["players"].append(str(msg.from_user.id))
    mp_matches[mid]["scores"][str(msg.from_user.id)] = 0

    start_round(mid)

# ========= RATING =========
@bot.message_handler(func=lambda m: m.text == "🏆 Рейтинг")
def rating(msg):
    bot.send_message(msg.chat.id, "Выберите рейтинг:", reply_markup=rating_menu())

@bot.callback_query_handler(func=lambda c: c.data == "top_season")
def top_season(call):
    s = season()
    top = sorted(users.values(), key=lambda x: x["season_scores"].get(s, 0), reverse=True)[:10]
    text = f"🏆 ТОП сезона {s}\n"
    for i, u in enumerate(top, 1):
        text += f"{i}. {u['name']} — {u['season_scores'].get(s,0)}\n"
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda c: c.data == "top_all")
def top_all(call):
    top = sorted(users.values(), key=lambda x: x["score"], reverse=True)[:10]
    text = "🌍 Глобальный ТОП\n"
    for i, u in enumerate(top, 1):
        text += f"{i}. {u['name']} — {u['score']}\n"
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda c: c.data == "top_all")
def top_all(call):
    top = sorted(users.values(), key=lambda x: x["score"], reverse=True)[:10]

    text = "🌍 *Глобальный рейтинг*\n\n"
    for i, u in enumerate(top, 1):
        text += f"{i}. {u['name']} — {u['score']}⭐\n"

    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

# ========= STATS =========
@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stats(msg):
    u = get_user(msg.from_user.id)
    bot.send_message(
        msg.chat.id,
        f"👤 {u['name']}\n"
        f"🎮 Игр: {u['games']}\n"
        f"🏆 Побед: {u['wins']}\n"
        f"🌍 Очки: {u['score']}"
    )

# ========= HELP =========
@bot.message_handler(func=lambda m: m.text == "ℹ️ Помощь")
def help_(msg):
    bot.send_message(
        msg.chat.id,
        "📘 Учите элементы\n🧪 Играйте\n👥 Сражайтесь\n🏆 Попадайте в топ!\n🕶Гайд на бота - @fractaldevelopment"
    )

# ========= ADMIN =========
@bot.message_handler(commands=["code"])
def admin_code(msg):
    if msg.text.strip().endswith(ADMIN_CODE):
        admins.add(msg.from_user.id)
        bot.send_message(
            msg.chat.id,
            "👮 Админ-доступ получен",
            reply_markup=admin_menu()
        )
    else:
        bot.send_message(msg.chat.id, "❌ Неверный код")

def find_user_by_name_or_id(query):
    # если это ID
    if query.isdigit() and query in users:
        return query

    # иначе ищем по имени
    for uid, u in users.items():
        if u.get("name") == query:
            return uid

    return None



@bot.message_handler(func=lambda m: m.text == "⬅ Назад" and m.from_user.id in admins)
def admin_back(msg):
    bot.send_message(msg.chat.id, "Главное меню", reply_markup=main_menu())

admin_give_state = {}

@bot.message_handler(func=lambda m: m.text == "🎁 Выдать достижение" and m.from_user.id in admins)
def admin_give_start(msg):
    bot.send_message(msg.chat.id, "Введите ID пользователя:")
    bot.register_next_step_handler(msg, admin_give_uid)

def admin_give_uid(msg):
    admin_give_state[msg.from_user.id] = msg.text.strip()
    bot.send_message(msg.chat.id, "Введите текст достижения:")
    bot.register_next_step_handler(msg, admin_give_text)

def admin_give_text(msg):
    query = admin_give_state.pop(msg.from_user.id)

    uid = find_user_by_name_or_id(query)
    if not uid:
        bot.send_message(msg.chat.id, "❌ Пользователь не найден")
        return

    u = get_user(uid)

    text = msg.text.strip()
    key = f"custom_{uuid.uuid4()}"

    u["custom_achievements"].append({
        "id": key,
        "name": text,
    })
    save_users()

    bot.send_message(
        int(uid),
        f"🏅 *Вы получили достижение!*\n{text}",
        parse_mode="Markdown"
    )
    bot.send_message(msg.chat.id, "✅ Достижение выдано")



@bot.message_handler(func=lambda m: m.text == "🛠Сменить имя")
def rename_start(msg):
    rename_mode.add(msg.chat.id)
    bot.send_message(msg.chat.id, "Введите новое имя")

@bot.message_handler(func=lambda m: m.chat.id in rename_mode)
def rename_finish(msg):
    rename_mode.discard(msg.chat.id)
    u = get_user(msg.from_user.id)
    u["name"] = msg.text.strip()[:20]
    save_users()
    bot.send_message(msg.chat.id, "✅Имя изменено", reply_markup=main_menu())


def check_achievements(uid):
    u = get_user(uid)
    gained = []

    for key, a in ACHIEVEMENTS.items():
        if key in u["achievements"]:
            continue

        current = u["games"] if a["type"] == "games" else u["wins"]

        if current >= a["goal"]:
            u["achievements"].append(key)

            reward = a.get("reward", 0)
            if reward > 0:
                u["score"] += reward

            gained.append(
                f"{a['name']}" + (f" (+{reward}⭐)" if reward else "")
            )

    if a["type"] == "streak":
        current = u["day_streak"]

    if gained:
        save_users()
        bot.send_message(
            int(uid),
            "🏅 *Новое достижение!*\n\n" + "\n".join(gained),
            parse_mode="Markdown"
        )

@bot.message_handler(func=lambda m: m.text == "🏅 Достижения")
def achievements(msg):
    u = get_user(msg.from_user.id)

    text = "🏅 *Достижения*\n\n"

    # 🎯 Системные достижения
    for key, a in ACHIEVEMENTS.items():
        if a["hidden"] and key not in u["achievements"]:
            text += "❓ *Скрытое достижение*\n\n"
            continue

        progress = u["games"] if a["type"] == "games" else u["wins"]
        percent = min(100, int(progress / a["goal"] * 100))
        status = "✅" if key in u["achievements"] else "🔒"

        text += (
            f"{status} *{a['name']}*\n"
            f"{a['desc']}\n"
            f"Прогресс: {progress}/{a['goal']} ({percent}%)\n\n"
        )

    # 🎁 Админские достижения
    if u.get("custom_achievements"):
        text += "🎁 *Особые достижения*\n\n"
        for a in u["custom_achievements"]:
            text += f"🏅 {a['name']}\n"

    bot.send_message(
        msg.chat.id,
        text,
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

# ========= RUN =========
bot.infinity_polling()
