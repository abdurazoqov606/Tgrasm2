#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║         🤖 VSF AI PHOTO BOT — PREMIUM EDITION               ║
║         Muallif : @vsf911                                    ║
║         Kanal   : @vsf_lvl                                   ║
║         Versiya : 9.1.1                                 ║
╚══════════════════════════════════════════════════════════════╝
"""

import telebot
import requests
import urllib3
import time
import hashlib
import base64
import random
import json
import re
import sqlite3
import threading
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from telebot import types
from functools import wraps
from datetime import datetime, timedelta

urllib3.disable_warnings()

# ─────────────────────────────────────────────────────────────
#  ⚙️  ASOSIY SOZLAMALAR
# ─────────────────────────────────────────────────────────────
BOT_TOKEN   = "8421386543:AAEgPIYr6lbYbAAH-rOgkRM4FWJ2hx1bfFI"
ADMIN_IDS   = [8426582765]                 # Admin ID lar ro'yxati
BOT_VERSION = "9.1.1"
BOT_NAME    = "VSF AI RASM BOT"
AUTHOR      = "@vsf911"
DB_FILE     = "vsf_bot.db"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# ─────────────────────────────────────────────────────────────
#  🌐 RENDER.COM UCHUN SOXTA VEB-SERVER (DUMMY SERVER)
# ─────────────────────────────────────────────────────────────
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is successfully running on Render!")

    def log_message(self, format, *args):
        # Keraksiz loglarni yashirish uchun
        pass

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    print(f"🌐 Render.com uchun veb-server ishga tushdi (Port: {port})")
    server.serve_forever()

# ─────────────────────────────────────────────────────────────
#  🗄️  MA'LUMOTLAR BAZASI
# ─────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            uid         INTEGER PRIMARY KEY,
            username    TEXT,
            full_name   TEXT,
            lang        TEXT DEFAULT 'uz',
            is_premium  INTEGER DEFAULT 0,
            is_banned   INTEGER DEFAULT 0,
            joined_at   TEXT DEFAULT (datetime('now')),
            last_seen   TEXT DEFAULT (datetime('now')),
            gen_count   INTEGER DEFAULT 0,
            total_gens  INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS channels (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT UNIQUE,
            title       TEXT,
            is_active   INTEGER DEFAULT 1,
            added_at    TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS broadcasts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            text        TEXT,
            sent_count  INTEGER DEFAULT 0,
            fail_count  INTEGER DEFAULT 0,
            sent_at     TEXT DEFAULT (datetime('now')),
            admin_id    INTEGER
        );
        CREATE TABLE IF NOT EXISTS user_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            uid         INTEGER,
            prompt      TEXT,
            style       TEXT,
            aspect      TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS stats (
            key         TEXT PRIMARY KEY,
            value       TEXT
        );
        INSERT OR IGNORE INTO channels (username, title) VALUES ('@vsf_lvl', 'VSF Level');
    """)
    conn.commit()
    conn.close()

def get_db():
    return sqlite3.connect(DB_FILE)

def register_user(uid, username, full_name):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO users (uid, username, full_name)
        VALUES (?, ?, ?)
    """, (uid, username or "", full_name or ""))
    c.execute("""
        UPDATE users SET username=?, full_name=?, last_seen=datetime('now')
        WHERE uid=?
    """, (username or "", full_name or "", uid))
    conn.commit()
    conn.close()

def get_user(uid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE uid=?", (uid,))
    row = c.fetchone()
    conn.close()
    if row:
        keys = ["uid","username","full_name","lang","is_premium","is_banned",
                "joined_at","last_seen","gen_count","total_gens"]
        return dict(zip(keys, row))
    return None

def set_user_lang(uid, lang):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET lang=? WHERE uid=?", (lang, uid))
    conn.commit()
    conn.close()

def increment_gen(uid):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET gen_count=gen_count+1, total_gens=total_gens+1 WHERE uid=?", (uid,))
    conn.commit()
    conn.close()

def get_channels():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT username, title FROM channels WHERE is_active=1")
    rows = c.fetchall()
    conn.close()
    return rows

def add_channel(username, title=""):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT OR REPLACE INTO channels (username, title, is_active) VALUES (?,?,1)",
                  (username, title))
        conn.commit()
        result = True
    except Exception:
        result = False
    conn.close()
    return result

def remove_channel(username):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE channels SET is_active=0 WHERE username=?", (username,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT uid FROM users WHERE is_banned=0")
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows

def get_stats():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE last_seen >= datetime('now','-1 day')")
    active_day = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE last_seen >= datetime('now','-7 day')")
    active_week = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE joined_at >= datetime('now','-1 day')")
    new_today = c.fetchone()[0]
    c.execute("SELECT SUM(total_gens) FROM users")
    total_gens = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM channels WHERE is_active=1")
    channels = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM broadcasts")
    broadcasts = c.fetchone()[0]
    conn.close()
    return {
        "total": total,
        "active_day": active_day,
        "active_week": active_week,
        "new_today": new_today,
        "total_gens": total_gens,
        "channels": channels,
        "broadcasts": broadcasts
    }

def add_history(uid, prompt, style, aspect):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO user_history (uid, prompt, style, aspect) VALUES (?,?,?,?)",
              (uid, prompt, style, aspect))
    conn.commit()
    conn.close()

def get_history(uid, limit=10):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT prompt, style, aspect, created_at FROM user_history WHERE uid=? ORDER BY id DESC LIMIT ?",
              (uid, limit))
    rows = c.fetchall()
    conn.close()
    return rows

def ban_user(uid):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned=1 WHERE uid=?", (uid,))
    conn.commit()
    conn.close()

def unban_user(uid):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned=0 WHERE uid=?", (uid,))
    conn.commit()
    conn.close()

# ─────────────────────────────────────────────────────────────
#  🌐  KO'P TILLI MATNLAR
# ─────────────────────────────────────────────────────────────
TEXTS = {
    "uz": {
        "choose_lang":     "🌐 Tilni tanlang:\n\nIltimos, qulay tilni tanlang:",
        "lang_set":        "✅ Til o'zbekcha qilib belgilandi!",
        "welcome": (
            "╔══════════════════════════╗\n"
            "║   ✨ VSF AI PHOTO BOT ✨  ║\n"
            "╚══════════════════════════╝\n\n"
            "👋 Xush kelibsiz, {name}!\n\n"
            "🎨 70+ stil bilan AI rasm yarating\n"
            "⚡ Tez va sifatli natijalar\n"
            "🖼 Fon olib tashlash imkoniyati\n"
            "🎲 Tasodifiy g'oyalar\n\n"
            "📌 Muallif: @vsf911\n"
            "📢 Kanal: @vsf_lvl\n\n"
            "⬇️ Quyidan stilni tanlang:"
        ),
        "sub_required": (
            "🔒 Botdan foydalanish uchun\n"
            "quyidagi kanalga obuna bo'ling:\n\n"
            "📢 {channels}\n\n"
            "Obuna bo'lgach ✅ tugmasini bosing."
        ),
        "sub_channel":     "📢 Kanalga o'tish",
        "sub_check":       "✅ Obunani tekshirish",
        "sub_ok":          "✅ Obuna tasdiqlandi! Davom eting.",
        "sub_fail":        "❌ Hali obuna bo'lmadingiz!",
        "select_style":    "🎨 Stilni tanlang:",
        "select_aspect":   "📐 Nisbatni tanlang:",
        "enter_prompt":    "✍️ Rasm tavsifini yozing:\n\n💡 Misol: «kosmosda yurgan mushuk»",
        "generating":      "⏳ Rasm yaratilmoqda...\n\n🎨 Stil: {style}\n📐 Nisbat: {aspect}\n✨ Yaxshilanmoqda...",
        "gen_done":        "✅ {count} ta rasm yaratildi!",
        "gen_fail":        "❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.",
        "no_bg":           "❌ Fonsiz rasm mavjud emas.",
        "no_cache":        "❌ Avvalgi rasm topilmadi.",
        "regen_started":   "🔄 Qayta yaratilmoqda...",
        "regen_done":      "✅ Rasm qayta yaratildi!",
        "regen_fail":      "❌ Qayta yaratishda xatolik.",
        "history_empty":   "📭 Tarixingiz bo'sh.",
        "history_title":   "📜 So'nggi so'rovlaringiz:\n━━━━━━━━━━━━━━━━\n",
        "help_text": (
            "❓ YORDAM\n━━━━━━━━━━━━━━━━\n\n"
            "1️⃣ Kanalga obuna bo'ling\n"
            "2️⃣ /start bosing\n"
            "3️⃣ Stil tanlang\n"
            "4️⃣ Nisbat tanlang\n"
            "5️⃣ Tavsif yozing\n"
            "6️⃣ Rasmni oling!\n\n"
            "🎨 70+ stil mavjud\n"
            "📐 10 ta nisbat\n"
            "🖼 Fon olib tashlash\n"
            "🎲 Tasodifiy g'oyalar\n"
            "📜 So'rovlar tarixi\n\n"
            "📌 Muallif: @vsf911\n"
            "📢 Kanal: @vsf_lvl"
        ),
        "aspects_text":    "📐 Mavjud nisbatlar:\n━━━━━━━━━━━━━━━━\n",
        "random_prompt":   "💡 Tasodifiy g'oya:\n\n«{prompt}»\n\nNusxa olib foydalaning!",
        "prompt_short":    "✏️ Kamida 3 ta harf kiriting.",
        "no_bg_photos":    "🎭 Fonsiz rasmlar:",
        "page_info":       "📖 Sahifa {page}/{total}",
        "main_menu":       "🏠 Bosh menyu",
        "back":            "🔙 Orqaga",
        "banned":          "🚫 Siz bloklangansiz. Admin: @vsf911",
        "use_start":       "👋 /start bosing",
        "settings":        "⚙️ Sozlamalar",
        "my_stats":        (
            "📊 Sizning statistikangiz:\n━━━━━━━━━━━━━━━━\n"
            "🆔 ID: {uid}\n"
            "👤 Ism: {name}\n"
            "🌐 Til: {lang}\n"
            "🖼 Jami rasmlar: {gens}\n"
            "📅 Qo'shilgan: {joined}\n"
            "🕐 Oxirgi kirish: {last}\n"
        ),
    },
    "ru": {
        "choose_lang":     "🌐 Выберите язык:\n\nПожалуйста, выберите удобный язык:",
        "lang_set":        "✅ Язык установлен на русский!",
        "welcome": (
            "╔══════════════════════════╗\n"
            "║   ✨ VSF AI PHOTO BOT ✨  ║\n"
            "╚══════════════════════════╝\n\n"
            "👋 Добро пожаловать, {name}!\n\n"
            "🎨 Создавайте AI-изображения в 70+ стилях\n"
            "⚡ Быстро и качественно\n"
            "🖼 Удаление фона\n"
            "🎲 Случайные идеи\n\n"
            "📌 Автор: @vsf911\n"
            "📢 Канал: @vsf_lvl\n\n"
            "⬇️ Выберите стиль:"
        ),
        "sub_required": (
            "🔒 Для использования бота\n"
            "подпишитесь на канал:\n\n"
            "📢 {channels}\n\n"
            "После подписки нажмите ✅."
        ),
        "sub_channel":     "📢 Перейти в канал",
        "sub_check":       "✅ Проверить подписку",
        "sub_ok":          "✅ Подписка подтверждена!",
        "sub_fail":        "❌ Вы ещё не подписались!",
        "select_style":    "🎨 Выберите стиль:",
        "select_aspect":   "📐 Выберите соотношение:",
        "enter_prompt":    "✍️ Опишите изображение:\n\n💡 Пример: «кот в космосе»",
        "generating":      "⏳ Генерация...\n\n🎨 Стиль: {style}\n📐 Формат: {aspect}\n✨ Улучшаем...",
        "gen_done":        "✅ Создано {count} изображений!",
        "gen_fail":        "❌ Ошибка. Попробуйте снова.",
        "no_bg":           "❌ Изображение без фона недоступно.",
        "no_cache":        "❌ Предыдущее изображение не найдено.",
        "regen_started":   "🔄 Перегенерация...",
        "regen_done":      "✅ Изображение перегенерировано!",
        "regen_fail":      "❌ Ошибка перегенерации.",
        "history_empty":   "📭 История пуста.",
        "history_title":   "📜 Последние запросы:\n━━━━━━━━━━━━━━━━\n",
        "help_text": (
            "❓ ПОМОЩЬ\n━━━━━━━━━━━━━━━━\n\n"
            "1️⃣ Подпишитесь на канал\n"
            "2️⃣ Нажмите /start\n"
            "3️⃣ Выберите стиль\n"
            "4️⃣ Выберите формат\n"
            "5️⃣ Введите описание\n"
            "6️⃣ Получите изображение!\n\n"
            "🎨 70+ стилей\n"
            "📐 10 форматов\n"
            "🖼 Удаление фона\n"
            "🎲 Случайные идеи\n"
            "📜 История запросов\n\n"
            "📌 Автор: @vsf911\n"
            "📢 Канал: @vsf_lvl"
        ),
        "aspects_text":    "📐 Доступные форматы:\n━━━━━━━━━━━━━━━━\n",
        "random_prompt":   "💡 Случайная идея:\n\n«{prompt}»\n\nСкопируйте и используйте!",
        "prompt_short":    "✏️ Введите минимум 3 символа.",
        "no_bg_photos":    "🎭 Фото без фона:",
        "page_info":       "📖 Стр. {page}/{total}",
        "main_menu":       "🏠 Главное меню",
        "back":            "🔙 Назад",
        "banned":          "🚫 Вы заблокированы. Админ: @vsf911",
        "use_start":       "👋 Используйте /start",
        "settings":        "⚙️ Настройки",
        "my_stats":        (
            "📊 Ваша статистика:\n━━━━━━━━━━━━━━━━\n"
            "🆔 ID: {uid}\n"
            "👤 Имя: {name}\n"
            "🌐 Язык: {lang}\n"
            "🖼 Всего изображений: {gens}\n"
            "📅 Добавлен: {joined}\n"
            "🕐 Последний вход: {last}\n"
        ),
    },
    "en": {
        "choose_lang":     "🌐 Choose language:\n\nPlease select your preferred language:",
        "lang_set":        "✅ Language set to English!",
        "welcome": (
            "╔══════════════════════════╗\n"
            "║   ✨ VSF AI PHOTO BOT ✨  ║\n"
            "╚══════════════════════════╝\n\n"
            "👋 Welcome, {name}!\n\n"
            "🎨 Generate AI images in 70+ styles\n"
            "⚡ Fast and high-quality results\n"
            "🖼 Background removal\n"
            "🎲 Random prompt ideas\n\n"
            "📌 Author: @vsf911\n"
            "📢 Channel: @vsf_lvl\n\n"
            "⬇️ Choose a style below:"
        ),
        "sub_required": (
            "🔒 To use this bot,\n"
            "subscribe to our channel:\n\n"
            "📢 {channels}\n\n"
            "After subscribing, press ✅."
        ),
        "sub_channel":     "📢 Go to Channel",
        "sub_check":       "✅ Check Subscription",
        "sub_ok":          "✅ Subscription confirmed!",
        "sub_fail":        "❌ You haven't subscribed yet!",
        "select_style":    "🎨 Choose a style:",
        "select_aspect":   "📐 Choose an aspect ratio:",
        "enter_prompt":    "✍️ Describe your image:\n\n💡 Example: «a cat in space»",
        "generating":      "⏳ Generating...\n\n🎨 Style: {style}\n📐 Aspect: {aspect}\n✨ Enhancing...",
        "gen_done":        "✅ {count} image(s) generated!",
        "gen_fail":        "❌ Error occurred. Please try again.",
        "no_bg":           "❌ No background-removed image available.",
        "no_cache":        "❌ No previous image found.",
        "regen_started":   "🔄 Regenerating...",
        "regen_done":      "✅ Image regenerated!",
        "regen_fail":      "❌ Regeneration failed.",
        "history_empty":   "📭 Your history is empty.",
        "history_title":   "📜 Recent Prompts:\n━━━━━━━━━━━━━━━━\n",
        "help_text": (
            "❓ HELP\n━━━━━━━━━━━━━━━━\n\n"
            "1️⃣ Subscribe to channel\n"
            "2️⃣ Press /start\n"
            "3️⃣ Choose style\n"
            "4️⃣ Choose aspect ratio\n"
            "5️⃣ Enter description\n"
            "6️⃣ Get your image!\n\n"
            "🎨 70+ styles\n"
            "📐 10 aspect ratios\n"
            "🖼 Background removal\n"
            "🎲 Random prompts\n"
            "📜 Request history\n\n"
            "📌 Author: @vsf911\n"
            "📢 Channel: @vsf_lvl"
        ),
        "aspects_text":    "📐 Available Aspect Ratios:\n━━━━━━━━━━━━━━━━\n",
        "random_prompt":   "💡 Random Idea:\n\n«{prompt}»\n\nCopy and use it!",
        "prompt_short":    "✏️ Enter at least 3 characters.",
        "no_bg_photos":    "🎭 Background-removed photos:",
        "page_info":       "📖 Page {page}/{total}",
        "main_menu":       "🏠 Main Menu",
        "back":            "🔙 Back",
        "banned":          "🚫 You are banned. Admin: @vsf911",
        "use_start":       "👋 Use /start",
        "settings":        "⚙️ Settings",
        "my_stats":        (
            "📊 Your Statistics:\n━━━━━━━━━━━━━━━━\n"
            "🆔 ID: {uid}\n"
            "👤 Name: {name}\n"
            "🌐 Lang: {lang}\n"
            "🖼 Total images: {gens}\n"
            "📅 Joined: {joined}\n"
            "🕐 Last seen: {last}\n"
        ),
    }
}

def T(uid_or_lang, key, **kwargs):
    """Til bo'yicha matn olish"""
    if isinstance(uid_or_lang, int):
        user = get_user(uid_or_lang)
        lang = user["lang"] if user else "uz"
    else:
        lang = uid_or_lang
    lang = lang if lang in TEXTS else "uz"
    text = TEXTS[lang].get(key, TEXTS["uz"].get(key, ""))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception:
            pass
    return text

# ─────────────────────────────────────────────────────────────
#  🎨  STILLAR, NISBATLAR VA BOSHQALAR
# ─────────────────────────────────────────────────────────────
STYLES = [
    ("anime",         "🎌 Anime"),
    ("realistic",     "📸 Realistik"),
    ("oil_painting",  "🖼 Moy boya"),
    ("watercolor",    "💧 Akvarell"),
    ("sketch",        "✏️ Eskiz"),
    ("pixel",         "📟 Pixel Art"),
    ("3d_render",     "🎮 3D Render"),
    ("cyberpunk",     "🤖 Kiberpank"),
    ("steampunk",     "⚙️ Stimpank"),
    ("fantasy",       "🐉 Fantaziya"),
    ("gothic",        "🦇 Gotik"),
    ("cartoon",       "📺 Multfilm"),
    ("comic",         "💥 Komiks"),
    ("glitch",        "📺 Glitch"),
    ("vaporwave",     "🌴 Vaporwave"),
    ("impressionist", "🎨 Impressionizm"),
    ("expressionist", "😱 Ekspressionizm"),
    ("cubist",        "🔺 Kubizm"),
    ("surrealist",    "🌀 Syurrealizm"),
    ("popart",        "🍅 Pop Art"),
    ("minimalist",    "⬜ Minimalizm"),
    ("baroque",       "👑 Barokko"),
    ("rococo",        "🌸 Rokoko"),
    ("renaissance",   "🏛 Renessans"),
    ("abstract",      "🌀 Abstrakt"),
    ("graffiti",      "🎨 Graffiti"),
    ("vector",        "📐 Vektor"),
    ("isometric",     "📦 Izometrik"),
    ("low_poly",      "🔺 Low Poly"),
    ("chalk",         "🧵 Bo'r"),
    ("pastel",        "🌸 Pastel"),
    ("charcoal",      "⚫ Ko'mir"),
    ("mosaic",        "🟦 Mozaika"),
    ("origami",       "📄 Origami"),
    ("lego",          "🧱 Lego"),
    ("collage",       "📰 Kollaj"),
    ("mandala",       "🕉 Mandala"),
    ("calligraphy",   "✍️ Kalligrafiya"),
    ("polaroid",      "📸 Polaroid"),
    ("infrared",      "🔥 Infraqizil"),
    ("thermal",       "🌡 Issiqlik"),
    ("underwater",    "🌊 Suv osti"),
    ("microscopic",   "🔬 Mikroskopik"),
    ("telescopic",    "🔭 Teleskopik"),
    ("night_vision",  "🌙 Tungi ko'rinish"),
    ("xray",          "🦴 Rentgen"),
    ("hologram",      "👻 Hologram"),
    ("neon",          "💡 Neon"),
    ("chromatic",     "🌈 Xromatik"),
    ("monochrome",    "⚫ Qora-oq"),
    ("sepia",         "🟤 Sepia"),
    ("lomography",    "🎞 Lomografiya"),
    ("tilt_shift",    "🏠 Tilt Shift"),
    ("macro",         "🐞 Makro"),
    ("bokeh",         "💫 Bokeh"),
    ("long_exp",      "🌌 Uzun ekspozitsiya"),
    ("double_exp",    "👥 Qo'sh ekspozitsiya"),
    ("hdr",           "🌅 HDR"),
    ("night_mode",    "🌙 Tun rejimi"),
    ("portrait",      "👤 Portret"),
    ("landscape",     "🏔 Manzara"),
    ("street",        "🚦 Ko'cha"),
    ("architecture",  "🏛 Arxitektura"),
    ("food",          "🍔 Ovqat"),
    ("fashion",       "👗 Moda"),
    ("product",       "📦 Mahsulot"),
    ("automotive",    "🚗 Mashina"),
    ("sports",        "⚽ Sport"),
    ("wildlife",      "🦁 Hayvonot"),
    ("astro",         "⭐ Astronomiya"),
    ("aerial",        "🛩 Aerofoto"),
]

ASPECTS = [
    ("1:1",  "🟥 Kvadrat (1:1)"),
    ("4:5",  "📱 Portret (4:5)"),
    ("16:9", "🎬 Kino (16:9)"),
    ("9:16", "📲 Story (9:16)"),
    ("4:3",  "🖼 Klassik (4:3)"),
    ("3:4",  "📋 Vertikal (3:4)"),
    ("2:1",  "🌅 Panorama (2:1)"),
    ("21:9", "🌄 Ultra keng (21:9)"),
    ("5:4",  "🖼 Foto (5:4)"),
    ("1:2",  "📏 Uzun (1:2)"),
]

ASPECT_MAP = {
    "1:1":  "SQUARE_HD",
    "4:5":  "PORTRAIT_4_3",
    "16:9": "LANDSCAPE_16_9",
    "9:16": "PORTRAIT_16_9",
    "4:3":  "LANDSCAPE_4_3",
    "3:4":  "PORTRAIT_4_3",
    "2:1":  "LANDSCAPE_16_9",
    "21:9": "LANDSCAPE_16_9",
    "5:4":  "LANDSCAPE_4_3",
    "1:2":  "PORTRAIT_16_9",
}

ANGLES   = ["frnt_vw","sd_vw","bck_vw","tp_vw","btm_vw","prspctv","wd_ang","mcr_sh",
            "aerl","fsh_lns","tlt_shft","dth_ang","ovrhd","ye_lvl","brd_ye","wrm_ye"]
LIGHTS   = ["gldn_hr","nn_ngh","std_soft","drm_shdw","vlmtrc_fg","rm_lght","cnmtc_amb",
            "bl_md","wrm_snst","cld_wntr","snrse","mnlght","cndl_lght","flsh_ph","rng_lght"]
MOODS    = ["epc","clm","mystr","rmntc","drk_hrr","drmy","ftrsc","vntg_rtr","grng",
            "mnmlst","lxry","brtlst","chc","pcfl","mlnchlc","jyfl","hpfl","elgnt"]
FILTERS  = ["kdk_prtr","fj_prv","lfrd_bw","cnstl_800","plrd_nst","lmchrm","gf_vst",
            "hssbl_nat","lc_m10","zs_dstgn","vntg_1970","nstgrm","vsc_c1","anlg_stl"]
CAMERAS  = ["sony_a7riv","canon_r5","nikon_z9","fujifilm_gfx100","hasselblad_h6d",
            "leica_m11","iphone_15_pro","google_pixel_8","samsung_s24_ultra","oneplus_12"]
ARTISTS  = ["picasso","vangogh","monet","rembrandt","da_vinci","michelangelo","dali",
            "kandinsky","klimt","hopper","banksy","warhol","basquiat","pollock","rothko"]

RANDOM_PROMPTS_UZ = [
    "kosmosda yurgan mushuk", "oltin shahardan uchgan ajdaho", "sehrli o'rmondagi pari",
    "kelajakdagi robot shahri", "suv ostidagi qal'a", "bulutlar ustidagi bog'",
    "oy yuzida fonar'bop ovchi", "qorli tog'da yolg'iz bo'ri", "neon chiroqli kiberpank ko'chasi",
    "eski zarbxonadagi tilsim", "kosmosdan qaraydigan kos'monavt", "dengiz tubidagi xazina",
    "suv parilarining to'yi", "galaktikalar orasida suzuvchi kit", "ulkan qo'ziqorinlar o'rmoni",
    "kristall tog'lar ortidagi quyosh", "koinotda adashgan yulduz kemasi",
    "eski fotosuratdagi sirli qiz", "shamolda uchayotgan qit'a",
    "vulqon ustidagi qasr", "noan'anaviy yashash makoni",
]
RANDOM_PROMPTS_RU = [
    "кот в космосе", "дракон над золотым городом", "эльф в волшебном лесу",
    "город роботов будущего", "замок под водой", "сад над облаками",
    "охотник на луне с фонарём", "одинокий волк в снегу", "киберпанк переулок с неоном",
    "кит в галактике", "русалки на свадьбе", "сокровища на дне океана",
    "корабль потерявшийся в космосе", "лес гигантских грибов", "закат за хрустальными горами",
]
RANDOM_PROMPTS_EN = [
    "a cat in space", "dragon over a golden city", "elf in enchanted forest",
    "robot city of the future", "underwater castle", "garden above the clouds",
    "lone wolf in snow", "cyberpunk neon alley", "whale in a galaxy",
    "mermaids at a wedding", "treasure at ocean floor", "lost spaceship in cosmos",
    "giant mushroom forest", "sunset behind crystal mountains",
]

STYLE_DICT   = dict(STYLES)
ASPECT_DICT  = dict(ASPECTS)

# ─────────────────────────────────────────────────────────────
#  🛠  YORDAMCHI FUNKSIYALAR
# ─────────────────────────────────────────────────────────────
def _h(s):
    return hashlib.sha256(s.encode()).hexdigest()[:16]

def _c(p):
    return base64.b64encode(p.encode()).decode()

def _enh(p, sid):
    """Promptni yaxshilash"""
    a = random.choice(ANGLES).replace("_", " ")
    l = random.choice(LIGHTS).replace("_", " ")
    m = random.choice(MOODS).replace("_", " ")
    f = random.choice(FILTERS).replace("_", " ")
    c = random.choice(CAMERAS).replace("_", " ")
    is_art = sid in ["oil_painting","impressionist","surrealist","cubist","expressionist",
                     "renaissance","baroque","watercolor","sketch","mandala","calligraphy"]
    ar     = random.choice(ARTISTS) if is_art else ""
    ar_txt = f" style of {ar}" if ar else ""
    q      = random.choice([8, 12, 16, 24, 32])
    return (
        f"{p}, {a} view, {l} lighting, {m} atmosphere, {f} film, {c} camera{ar_txt}, "
        f"ultra hd {q}k, masterpiece, award winning, trending on artstation, "
        f"behance featured, cgsociety, highres, extremely detailed, professional"
    )

def _get_token():
    """PhotoRoom API uchun token olish"""
    headers = {
        'Content-Type': 'application/json',
        'X-Android-Package': 'com.photoroom.app',
        'X-Android-Cert': '0424A4898A4B33940D8BF16E44251B876E97F8D0',
        'Accept-Language': 'en-US',
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 12)',
        'Host': 'www.googleapis.com'
    }
    params = {'key': 'AIzaSyAJGrgbFGB_-h8V2oJLr4b-_ipetqM0duU'}
    body   = {'clientType': 'CLIENT_TYPE_ANDROID'}
    r = requests.post(
        'https://www.googleapis.com/identitytoolkit/v3/relyingparty/signupNewUser',
        headers=headers, params=params, json=body
    ).json()
    return r["idToken"]

def _generate_images(prompt, sid, asp):
    """Rasm yaratish"""
    sz  = ASPECT_MAP.get(asp, "SQUARE_HD")
    tkn = _get_token()
    rid = _h(f"{time.time()}{random.random()}{prompt[:10]}")
    headers = {
        'Host': 'serverless-api.photoroom.com',
        'Accept': 'text/event-stream',
        'Authorization': tkn,
        'Content-Type': 'application/json; charset=utf-8',
        'User-Agent': 'okhttp/4.12.0',
        'Pr-App-Version': '2025.47.03 (2180)',
        'Pr-Platform': 'android',
        'X-Request-ID': rid,
        'X-Enhanced': _c('true')
    }
    payload = {
        "userPrompt": _enh(prompt, sid),
        "appId": "expert",
        "styleId": sid,
        "sizeId": sz,
        "numberOfImages": 4,
        "cfgScale": 9,
        "steps": 45,
        "sampler": "dpmpp_2m_karras",
        "seed": random.randint(1, 999999999),
        "clip_skip": 2,
        "hires_fix": True,
        "denoising": 0.75,
        "face_restore": True,
        "upscale": 2
    }
    rs = requests.post(
        "https://serverless-api.photoroom.com/v2/ai-tools/generate-images",
        headers=headers, json=payload, stream=True, verify=False, timeout=180
    )
    bg, nb = [], []
    for line in rs.iter_lines():
        if not line:
            continue
        L = line.decode(errors='ignore')
        if '"eventType":"aiImageResult"' in L:
            s = L.find('"imageUrl":"') + 12
            e = L.find('"', s)
            if s > 12:
                bg.append(L[s:e])
        if '"eventType":"aiImageWithoutBackgroundResult"' in L:
            s = L.find('"imageUrl":"') + 12
            e = L.find('"', s)
            if s > 12:
                nb.append(L[s:e])
    return bg, nb

# ─────────────────────────────────────────────────────────────
#  🔒  TEKSHIRISH DECORATORLARI
# ─────────────────────────────────────────────────────────────
user_state = {}   # {uid: "awp" | ...}
user_data  = {}   # {uid: {sid, asp, p}}
img_cache  = {}   # {uid: {p, sid, asp, bg, nb}}
temp_data  = {}   # admin uchun vaqtinchalik ma'lumotlar

def is_subscribed(uid):
    """Barcha majburiy kanallarga obuna bo'lganini tekshirish"""
    channels = get_channels()
    for (ch, _) in channels:
        try:
            status = bot.get_chat_member(ch, uid).status
            if status not in ('member', 'administrator', 'creator'):
                return False
        except Exception:
            return False
    return True

def check_sub(func):
    """Obuna tekshirish decorator"""
    @wraps(func)
    def wrapper(message):
        uid  = message.from_user.id
        user = get_user(uid)
        if user and user.get("is_banned"):
            bot.reply_to(message, T(uid, "banned"))
            return
        if not is_subscribed(uid):
            send_sub_required(uid, message.chat.id)
            return
        return func(message)
    return wrapper

def send_sub_required(uid, chat_id=None):
    """Obuna talab qilingan xabar yuborish"""
    if chat_id is None:
        chat_id = uid
    channels = get_channels()
    ch_list  = "\n".join([f"• {ch}" for ch, _ in channels])
    lang     = get_user(uid)["lang"] if get_user(uid) else "uz"
    text     = T(lang, "sub_required", channels=ch_list)
    kb       = types.InlineKeyboardMarkup()
    for (ch, title) in channels:
        ch_clean = ch.lstrip("@")
        btn_text = f"📢 {title or ch}"
        kb.add(types.InlineKeyboardButton(btn_text, url=f"https://t.me/{ch_clean}"))
    kb.add(types.InlineKeyboardButton(T(lang, "sub_check"), callback_data="chk_sub"))
    bot.send_message(chat_id, text, reply_markup=kb)

def is_admin(uid):
    return uid in ADMIN_IDS

# ─────────────────────────────────────────────────────────────
#  🎛  KLAVIATURALAR
# ─────────────────────────────────────────────────────────────
def make_styles_keyboard(page=1, lang="uz"):
    items_per_page = 15
    start = (page - 1) * items_per_page
    end   = min(start + items_per_page, len(STYLES))
    kb    = types.InlineKeyboardMarkup(row_width=3)
    for sid, sname in STYLES[start:end]:
        kb.add(types.InlineKeyboardButton(sname, callback_data=f"st:{sid}"))
    total_pages = (len(STYLES) + items_per_page - 1) // items_per_page
    nav = []
    if page > 1:
        nav.append(types.InlineKeyboardButton("◀️", callback_data=f"pg:{page-1}"))
    nav.append(types.InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if end < len(STYLES):
        nav.append(types.InlineKeyboardButton("▶️", callback_data=f"pg:{page+1}"))
    if nav:
        kb.row(*nav)
    kb.row(
        types.InlineKeyboardButton("🎲 " + ("Tasodifiy" if lang=="uz" else "Случайный" if lang=="ru" else "Random"),
                                   callback_data="rnd_pr"),
        types.InlineKeyboardButton("📐 " + ("Nisbatlar" if lang=="uz" else "Форматы" if lang=="ru" else "Ratios"),
                                   callback_data="as_ls")
    )
    kb.row(
        types.InlineKeyboardButton("📜 " + ("Tarix" if lang=="uz" else "История" if lang=="ru" else "History"),
                                   callback_data="hst"),
        types.InlineKeyboardButton("📊 " + ("Statistika" if lang=="uz" else "Статистика" if lang=="ru" else "Stats"),
                                   callback_data="my_stats"),
        types.InlineKeyboardButton("❓ " + ("Yordam" if lang=="uz" else "Помощь" if lang=="ru" else "Help"),
                                   callback_data="hlp")
    )
    kb.row(
        types.InlineKeyboardButton("🌐 " + ("Til" if lang=="uz" else "Язык" if lang=="ru" else "Language"),
                                   callback_data="ch_lang")
    )
    return kb

def make_aspects_keyboard(sid, lang="uz"):
    kb = types.InlineKeyboardMarkup(row_width=2)
    for asp, aname in ASPECTS:
        kb.add(types.InlineKeyboardButton(aname, callback_data=f"ap:{asp}:{sid}"))
    kb.add(types.InlineKeyboardButton(T(lang, "back"), callback_data="hm"))
    return kb

def make_post_gen_keyboard(lang="uz"):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🔄 " + ("Qayta" if lang=="uz" else "Заново" if lang=="ru" else "Regen"),
                                   callback_data="rg"),
        types.InlineKeyboardButton("🎭 " + ("Fonsiz" if lang=="uz" else "Без фона" if lang=="ru" else "No BG"),
                                   callback_data="nb")
    )
    kb.add(
        types.InlineKeyboardButton("🏠 " + ("Bosh menyu" if lang=="uz" else "Главная" if lang=="ru" else "Home"),
                                   callback_data="hm"),
        types.InlineKeyboardButton("🎨 " + ("Yangi stil" if lang=="uz" else "Новый стиль" if lang=="ru" else "New Style"),
                                   callback_data="ns")
    )
    return kb

# ─────────────────────────────────────────────────────────────
#  🚀  KOMANDALAR
# ─────────────────────────────────────────────────────────────
@bot.message_handler(commands=['start'])
def cmd_start(message):
    uid  = message.from_user.id
    name = message.from_user.first_name or "Foydalanuvchi"
    uname = message.from_user.username
    register_user(uid, uname, name)
    user = get_user(uid)
    if user and user.get("is_banned"):
        bot.send_message(uid, T("uz", "banned"))
        return
    if user and user.get("lang"):
        lang = user["lang"]
        if not is_subscribed(uid):
            send_sub_required(uid)
            return
        send_main_menu(uid, lang, name)
    else:
        send_lang_selection(uid)

def send_lang_selection(chat_id, edit_msg_id=None):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang:uz"),
        types.InlineKeyboardButton("🇷🇺 Русский",   callback_data="lang:ru"),
        types.InlineKeyboardButton("🇬🇧 English",   callback_data="lang:en"),
    )
    text = (
        "╔══════════════════════════╗\n"
        "║   ✨ VSF AI PHOTO BOT ✨  ║\n"
        "╚══════════════════════════╝\n\n"
        "🌐 Tilni tanlang / Выберите язык / Choose language:"
    )
    if edit_msg_id:
        try:
            bot.edit_message_text(text, chat_id, edit_msg_id, reply_markup=kb)
        except:
            bot.send_message(chat_id, text, reply_markup=kb)
    else:
        bot.send_message(chat_id, text, reply_markup=kb)

def send_main_menu(uid, lang, name=None):
    if name is None:
        user = get_user(uid)
        name = user["full_name"] if user else "Foydalanuvchi"
    text = T(lang, "welcome", name=name)
    kb   = make_styles_keyboard(page=1, lang=lang)
    bot.send_message(uid, text, reply_markup=kb)

@bot.message_handler(commands=['admin'])
def cmd_admin(message):
    uid = message.from_user.id
    if not is_admin(uid):
        bot.send_message(uid, "⛔ Ruxsat yo'q.")
        return
    send_admin_panel(uid)

@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    uid = message.from_user.id
    if not is_admin(uid):
        bot.send_message(uid, "⛔ Ruxsat yo'q.")
        return
    s = get_stats()
    text = (
             "📊 BOT STATISTIKASI\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Jami foydalanuvchilar : {s['total']}\n"
        f"📅 Bugun faol           : {s['active_day']}\n"
        f"📆 Hafta ichida faol    : {s['active_week']}\n"
        f"🆕 Bugun qo'shildi      : {s['new_today']}\n"
        f"🖼 Jami rasmlar         : {s['total_gens']}\n"
        f"📢 Kanallar             : {s['channels']}\n"
        f"📣 Xabar tarqatmalar    : {s['broadcasts']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 Bot versiya: {BOT_VERSION}\n"
        f"📌 Muallif: {AUTHOR}"
    )
    bot.send_message(uid, text)

@bot.message_handler(commands=['broadcast'])
def cmd_broadcast(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    temp_data[uid] = {"action": "broadcast"}
    bot.send_message(uid,
        "📣 Barcha foydalanuvchilarga yuboriladigan xabarni kiriting:\n\n"
        "(Bekor qilish uchun /cancel)"
    )

@bot.message_handler(commands=['cancel'])
def cmd_cancel(message):
    uid = message.from_user.id
    temp_data.pop(uid, None)
    user_state.pop(uid, None)
    user_data.pop(uid, None)
    lang = get_user(uid)["lang"] if get_user(uid) else "uz"
    bot.send_message(uid, "❌ Bekor qilindi." if lang=="uz" else "❌ Отменено." if lang=="ru" else "❌ Cancelled.")

@bot.message_handler(commands=['ban'])
def cmd_ban(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(uid, "❌ Foydalanish: /ban [user_id]")
        return
    try:
        target = int(parts[1])
        ban_user(target)
        bot.send_message(uid, f"✅ Foydalanuvchi {target} bloklandi.")
    except Exception as e:
        bot.send_message(uid, f"❌ Xatolik: {e}")

@bot.message_handler(commands=['unban'])
def cmd_unban(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(uid, "❌ Foydalanish: /unban [user_id]")
        return
    try:
        target = int(parts[1])
        unban_user(target)
        bot.send_message(uid, f"✅ Foydalanuvchi {target} blokdan chiqarildi.")
    except Exception as e:
        bot.send_message(uid, f"❌ Xatolik: {e}")

@bot.message_handler(commands=['addchannel'])
def cmd_add_channel(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(uid, "❌ Foydalanish: /addchannel @kanal_nomi [sarlavha]")
        return
    ch    = parts[1] if parts[1].startswith("@") else "@" + parts[1]
    title = " ".join(parts[2:]) if len(parts) > 2 else ch
    if add_channel(ch, title):
        bot.send_message(uid, f"✅ Kanal qo'shildi: {ch}")
    else:
        bot.send_message(uid, f"❌ Kanal qo'shib bo'lmadi.")

@bot.message_handler(commands=['removechannel'])
def cmd_remove_channel(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(uid, "❌ Foydalanish: /removechannel @kanal_nomi")
        return
    ch = parts[1] if parts[1].startswith("@") else "@" + parts[1]
    remove_channel(ch)
    bot.send_message(uid, f"✅ Kanal o'chirildi: {ch}")

@bot.message_handler(commands=['channels'])
def cmd_channels(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    channels = get_channels()
    if not channels:
        bot.send_message(uid, "📭 Hech qanday faol kanal yo'q.")
        return
    text = "📢 Faol majburiy kanallar:\n━━━━━━━━━━━━━━━━\n"
    for ch, title in channels:
        text += f"• {ch} — {title or '—'}\n"
    bot.send_message(uid, text)

# ─────────────────────────────────────────────────────────────
#  🔔  CALLBACK QUERY HANDLERLARI
# ─────────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("lang:"))
def cb_lang(c):
    uid  = c.from_user.id
    lang = c.data.split(":")[1]
    set_user_lang(uid, lang)
    bot.answer_callback_query(c.id, T(lang, "lang_set"))
    if not is_subscribed(uid):
        try:
            bot.delete_message(uid, c.message.message_id)
        except:
            pass
        send_sub_required(uid)
        return
    try:
        bot.delete_message(uid, c.message.message_id)
    except:
        pass
    user = get_user(uid)
    name = user["full_name"] if user else "Foydalanuvchi"
    send_main_menu(uid, lang, name)

@bot.callback_query_handler(func=lambda c: c.data == "ch_lang")
def cb_change_lang(c):
    uid = c.from_user.id
    send_lang_selection(uid, c.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "chk_sub")
def cb_check_sub(c):
    uid  = c.from_user.id
    lang = get_user(uid)["lang"] if get_user(uid) else "uz"
    if is_subscribed(uid):
        bot.answer_callback_query(c.id, T(lang, "sub_ok"), show_alert=True)
        try:
            bot.delete_message(uid, c.message.message_id)
        except:
            pass
        user = get_user(uid)
        name = user["full_name"] if user else "Foydalanuvchi"
        send_main_menu(uid, lang, name)
    else:
        bot.answer_callback_query(c.id, T(lang, "sub_fail"), show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data == "hm")
def cb_home(c):
    uid  = c.from_user.id
    user = get_user(uid)
    lang = user["lang"] if user else "uz"
    name = user["full_name"] if user else "Foydalanuvchi"
    user_state.pop(uid, None)
    if not is_subscribed(uid):
        try:
            bot.delete_message(uid, c.message.message_id)
        except:
            pass
        send_sub_required(uid)
        return
    text = T(lang, "welcome", name=name)
    kb   = make_styles_keyboard(page=1, lang=lang)
    try:
        bot.edit_message_text(text, c.message.chat.id, c.message.message_id, reply_markup=kb)
    except:
        bot.send_message(uid, text, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pg:"))
def cb_page(c):
    uid  = c.from_user.id
    lang = get_user(uid)["lang"] if get_user(uid) else "uz"
    page = int(c.data.split(":")[1])
    kb   = make_styles_keyboard(page=page, lang=lang)
    try:
        bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id, reply_markup=kb)
    except:
        pass
    bot.answer_callback_query(c.id)

@bot.callback_query_handler(func=lambda c: c.data == "noop")
def cb_noop(c):
    bot.answer_callback_query(c.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("st:"))
def cb_style(c):
    uid  = c.from_user.id
    lang = get_user(uid)["lang"] if get_user(uid) else "uz"
    if not is_subscribed(uid):
        send_sub_required(uid)
        return
    sid   = c.data.split(":")[1]
    sname = STYLE_DICT.get(sid, sid)
    user_data[uid] = {"sid": sid}
    kb = make_aspects_keyboard(sid, lang)
    text = f"✅ {sname}\n\n" + T(lang, "select_aspect")
    try:
        bot.edit_message_text(text, c.message.chat.id, c.message.message_id, reply_markup=kb)
    except:
        bot.send_message(uid, text, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ap:"))
def cb_aspect(c):
    uid  = c.from_user.id
    lang = get_user(uid)["lang"] if get_user(uid) else "uz"
    if not is_subscribed(uid):
        send_sub_required(uid)
        return
    parts = c.data.split(":")
    asp   = parts[1]
    sid   = parts[2]
    aname = ASPECT_DICT.get(asp, asp)
    sname = STYLE_DICT.get(sid, sid)
    if uid not in user_data:
        user_data[uid] = {}
    user_data[uid]["sid"] = sid
    user_data[uid]["asp"] = asp
    user_state[uid] = "awp"
    text = f"✅ {sname}\n✅ {aname}\n\n" + T(lang, "enter_prompt")
    try:
        bot.edit_message_text(text, c.message.chat.id, c.message.message_id)
    except:
        bot.send_message(uid, text)

@bot.callback_query_handler(func=lambda c: c.data == "hlp")
def cb_help(c):
    uid  = c.from_user.id
    lang = get_user(uid)["lang"] if get_user(uid) else "uz"
    kb   = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(T(lang, "back"), callback_data="hm"))
    try:
        bot.edit_message_text(T(lang, "help_text"), c.message.chat.id, c.message.message_id, reply_markup=kb)
    except:
        bot.send_message(uid, T(lang, "help_text"), reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "as_ls")
def cb_aspects_list(c):
    uid  = c.from_user.id
    lang = get_user(uid)["lang"] if get_user(uid) else "uz"
    text = T(lang, "aspects_text")
    for asp, aname in ASPECTS:
        text += f"▪️ {aname}\n"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(T(lang, "back"), callback_data="hm"))
    try:
        bot.edit_message_text(text, c.message.chat.id, c.message.message_id, reply_markup=kb)
    except:
        bot.send_message(uid, text, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "hst")
def cb_history(c):
    uid  = c.from_user.id
    lang = get_user(uid)["lang"] if get_user(uid) else "uz"
    rows = get_history(uid, 10)
    if not rows:
        bot.answer_callback_query(c.id, T(lang, "history_empty"), show_alert=True)
        return
    text = T(lang, "history_title")
    for i, (prompt, style, aspect, created_at) in enumerate(rows, 1):
        sname = STYLE_DICT.get(style, style)
        text += f"{i}️⃣ {prompt[:35]}...\n   └ {sname} | {aspect}\n"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(T(lang, "back"), callback_data="hm"))
    try:
        bot.edit_message_text(text, c.message.chat.id, c.message.message_id, reply_markup=kb)
    except:
        bot.send_message(uid, text, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "my_stats")
def cb_my_stats(c):
    uid  = c.from_user.id
    lang = get_user(uid)["lang"] if get_user(uid) else "uz"
    user = get_user(uid)
    if not user:
        bot.answer_callback_query(c.id)
        return
    lang_names = {"uz": "O'zbekcha 🇺🇿", "ru": "Русский 🇷🇺", "en": "English 🇬🇧"}
    text = T(lang, "my_stats",
        uid=uid,
        name=user["full_name"],
        lang=lang_names.get(lang, lang),
        gens=user["total_gens"],
        joined=user["joined_at"][:10],
        last=user["last_seen"][:16]
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(T(lang, "back"), callback_data="hm"))
    try:
        bot.edit_message_text(text, c.message.chat.id, c.message.message_id, reply_markup=kb)
    except:
        bot.send_message(uid, text, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "rnd_pr")
def cb_random_prompt(c):
    uid  = c.from_user.id
    lang = get_user(uid)["lang"] if get_user(uid) else "uz"
    if lang == "ru":
        prompt = random.choice(RANDOM_PROMPTS_RU)
    elif lang == "en":
        prompt = random.choice(RANDOM_PROMPTS_EN)
    else:
        prompt = random.choice(RANDOM_PROMPTS_UZ)
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("🎲 " + ("Yana" if lang=="uz" else "Ещё" if lang=="ru" else "Another"),
                                   callback_data="rnd_pr"),
        types.InlineKeyboardButton(T(lang, "back"), callback_data="hm")
    )
    try:
        bot.edit_message_text(T(lang, "random_prompt", prompt=prompt),
                              c.message.chat.id, c.message.message_id, reply_markup=kb)
    except:
        bot.send_message(uid, T(lang, "random_prompt", prompt=prompt), reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "rg")
def cb_regen(c):
    uid  = c.from_user.id
    lang = get_user(uid)["lang"] if get_user(uid) else "uz"
    if uid not in img_cache:
        bot.answer_callback_query(c.id, T(lang, "no_cache"), show_alert=True)
        return
    bot.answer_callback_query(c.id, T(lang, "regen_started"))
    cd = img_cache[uid]

    def do_regen():
        try:
            bg, nb = _generate_images(cd["p"], cd["sid"], cd["asp"])
            if bg:
                for url in bg:
                    bot.send_photo(uid, url)
                img_cache[uid] = {**cd, "bg": bg, "nb": nb}
                bot.send_message(uid, T(lang, "regen_done"), reply_markup=make_post_gen_keyboard(lang))
            else:
                bot.send_message(uid, T(lang, "regen_fail"))
        except Exception:
            bot.send_message(uid, T(lang, "regen_fail"))

    threading.Thread(target=do_regen, daemon=True).start()

@bot.callback_query_handler(func=lambda c: c.data == "nb")
def cb_no_bg(c):
    uid  = c.from_user.id
    lang = get_user(uid)["lang"] if get_user(uid) else "uz"
    if uid in img_cache and img_cache[uid].get("nb"):
        for url in img_cache[uid]["nb"]:
            bot.send_photo(uid, url, caption=T(lang, "no_bg_photos"))
    else:
        bot.answer_callback_query(c.id, T(lang, "no_bg"), show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data == "ns")
def cb_new_style(c):
    cb_home(c)

# ─────────────────────────────────────────────────────────────
#  🎛  ADMIN PANEL
# ─────────────────────────────────────────────────────────────
def send_admin_panel(uid):
    s    = get_stats()
    text = (
        "╔══════════════════════════╗\n"
        "║    🛡 ADMIN PANEL 🛡      ║\n"
        "╚══════════════════════════╝\n\n"
        f"👥 Foydalanuvchilar : {s['total']}\n"
        f"📅 Bugun faol       : {s['active_day']}\n"
        f"🆕 Yangi bugun      : {s['new_today']}\n"
        f"🖼 Jami rasmlar     : {s['total_gens']}\n"
        f"📢 Kanallar         : {s['channels']}\n\n"
        f"📌 Muallif: {AUTHOR}"
    )
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📣 Xabar tarqatish", callback_data="adm:broadcast"),
        types.InlineKeyboardButton("📊 Statistika",      callback_data="adm:stats"),
    )
    kb.add(
        types.InlineKeyboardButton("📢 Kanallar",        callback_data="adm:channels"),
        types.InlineKeyboardButton("🚫 Ban list",        callback_data="adm:banlist"),
    )
    kb.add(
        types.InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="adm:users"),
        types.InlineKeyboardButton("🔄 Yangilash",        callback_data="adm:refresh"),
    )
    kb.add(
        types.InlineKeyboardButton("📜 Buyruqlar",       callback_data="adm:cmds"),
    )
    bot.send_message(uid, text, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm:"))
def cb_admin(c):
    uid = c.from_user.id
    if not is_admin(uid):
        bot.answer_callback_query(c.id, "⛔ Ruxsat yo'q!", show_alert=True)
        return
    action = c.data.split(":")[1]

    if action == "refresh":
        bot.answer_callback_query(c.id, "🔄 Yangilandi!")
        try:
            bot.delete_message(uid, c.message.message_id)
        except:
            pass
        send_admin_panel(uid)

    elif action == "stats":
        s = get_stats()
        text = (
            "📊 TO'LIQ STATISTIKA\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Jami foydalanuvchilar : {s['total']}\n"
            f"📅 Bugun faol           : {s['active_day']}\n"
            f"📆 Hafta ichida faol    : {s['active_week']}\n"
            f"🆕 Bugun qo'shildi      : {s['new_today']}\n"
            f"🖼 Jami rasmlar         : {s['total_gens']}\n"
            f"📢 Faol kanallar        : {s['channels']}\n"
            f"📣 Tarqatmalar          : {s['broadcasts']}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data="adm:back"))
        bot.edit_message_text(text, uid, c.message.message_id, reply_markup=kb)

    elif action == "channels":
        channels = get_channels()
        text = "📢 Faol majburiy kanallar:\n━━━━━━━━━━━━━━━━\n"
        if channels:
            for ch, title in channels:
                text += f"• {ch} — {title or '—'}\n"
        else:
            text += "Hech qanday kanal yo'q.\n"
        text += (
            "\n📌 Kanal qo'shish: /addchannel @kanal [sarlavha]\n"
            "📌 Kanal o'chirish: /removechannel @kanal"
        )
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data="adm:back"))
        bot.edit_message_text(text, uid, c.message.message_id, reply_markup=kb)

    elif action == "broadcast":
        bot.answer_callback_query(c.id)
        temp_data[uid] = {"action": "broadcast"}
        bot.send_message(uid,
            "📣 Barcha foydalanuvchilarga yubormoqchi bo'lgan xabarni kiriting:\n\n"
            "📝 Matn, rasm, video — barchasi qo'llab-quvvatlanadi.\n"
            "❌ Bekor qilish: /cancel"
        )

    elif action == "users":
        conn = get_db()
        c2 = conn.cursor()
        c2.execute("SELECT uid, username, full_name, lang, total_gens, last_seen FROM users ORDER BY id DESC LIMIT 15")
        rows = c2.fetchall()
        conn.close()
        text = "👥 So'nggi foydalanuvchilar:\n━━━━━━━━━━━━━━━━\n"
        for row in rows:
            uname = f"@{row[1]}" if row[1] else "—"
            text += f"• {row[2]} ({uname}) | {row[3]} | 🖼{row[4]}\n"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data="adm:back"))
        try:
            bot.edit_message_text(text, uid, c.message.message_id, reply_markup=kb)
        except:
            bot.send_message(uid, text, reply_markup=kb)

    elif action == "banlist":
        conn = get_db()
        c2 = conn.cursor()
        c2.execute("SELECT uid, username, full_name FROM users WHERE is_banned=1")
        rows = c2.fetchall()
        conn.close()
        text = "🚫 Bloklangan foydalanuvchilar:\n━━━━━━━━━━━━━━━━\n"
        if rows:
            for row in rows:
                uname = f"@{row[1]}" if row[1] else "—"
                text += f"• {row[2]} ({uname}) | ID: {row[0]}\n"
        else:
            text += "Hech kim bloklanmagan.\n"
        text += "\n📌 /ban [id] | /unban [id]"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data="adm:back"))
        try:
            bot.edit_message_text(text, uid, c.message.message_id, reply_markup=kb)
        except:
            bot.send_message(uid, text, reply_markup=kb)

    elif action == "cmds":
        text = (
            "📜 ADMIN BUYRUQLARI\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "/admin — Admin panel\n"
            "/stats — Statistika\n"
            "/broadcast — Xabar tarqatish\n"
            "/addchannel @ch [nom] — Kanal qo'shish\n"
            "/removechannel @ch — Kanal o'chirish\n"
            "/channels — Kanallar ro'yxati\n"
            "/ban [id] — Bloklash\n"
            "/unban [id] — Blokni ochish\n"
            "/cancel — Amalni bekor qilish\n"
        )
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data="adm:back"))
        bot.edit_message_text(text, uid, c.message.message_id, reply_markup=kb)

    elif action == "back":
        try:
            bot.delete_message(uid, c.message.message_id)
        except:
            pass
        send_admin_panel(uid)

# ────────────────────────────────────────#  📝  MATN XABARLARI HANDLERI
# ─────────────────────────────────────────────────────────────
@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'animation', 'sticker'])
def handle_message(message):
    uid  = message.from_user.id
    lang = get_user(uid)["lang"] if get_user(uid) else "uz"
    user = get_user(uid)

    if user and user.get("is_banned"):
        bot.reply_to(message, T(lang, "banned"))
        return

    if not user:
        register_user(uid, message.from_user.username, message.from_user.first_name)

    if uid in temp_data and temp_data[uid].get("action") == "broadcast" and is_admin(uid):
        handle_broadcast_input(message, uid)
        return

    if user_state.get(uid) == "awp" and message.content_type == 'text':
        handle_prompt_input(message, uid, lang)
        return

    if message.content_type == 'text':
        if not user or not user.get("lang"):
            send_lang_selection(uid)
        else:
            if not is_subscribed(uid):
                send_sub_required(uid)
            else:
                bot.send_message(uid, T(lang, "use_start"))

def handle_prompt_input(message, uid, lang):
    if not is_subscribed(uid):
        user_state.pop(uid, None)
        send_sub_required(uid)
        return

    prompt = message.text.strip()
    if len(prompt) < 3:
        bot.reply_to(message, T(lang, "prompt_short"))
        return

    if uid not in user_data:
        bot.send_message(uid, T(lang, "use_start"))
        return

    sid   = user_data[uid].get("sid", "realistic")
    asp   = user_data[uid].get("asp", "1:1")
    sname = STYLE_DICT.get(sid, sid)
    aname = ASPECT_DICT.get(asp, asp)

    user_data[uid]["p"] = prompt
    user_state.pop(uid, None)

    wait_msg = bot.send_message(uid, T(lang, "generating", style=sname, aspect=aname))

    def do_gen():
        try:
            bg, nb = _generate_images(prompt, sid, asp)
        except Exception:
            try:
                bot.delete_message(uid, wait_msg.message_id)
            except:
                pass
            bot.send_message(uid, T(lang, "gen_fail"))
            return

        try:
            bot.delete_message(uid, wait_msg.message_id)
        except:
            pass

        if not bg:
            bot.send_message(uid, T(lang, "gen_fail"))
            return

        for url in bg:
            try:
                bot.send_photo(uid, url)
            except:
                pass

        img_cache[uid] = {"p": prompt, "sid": sid, "asp": asp, "bg": bg, "nb": nb}
        add_history(uid, prompt, sid, asp)
        increment_gen(uid)

        bot.send_message(uid,
            T(lang, "gen_done", count=len(bg)),
            reply_markup=make_post_gen_keyboard(lang)
        )

    threading.Thread(target=do_gen, daemon=True).start()

def handle_broadcast_input(message, admin_uid):
    temp_data.pop(admin_uid, None)
    all_users = get_all_users()
    total     = len(all_users)

    prog_msg = bot.send_message(admin_uid,
        f"📣 Yuborilmoqda...\n👥 Jami: {total} ta foydalanuvchi"
    )

    sent_count = 0
    fail_count = 0

    def do_broadcast():
        nonlocal sent_count, fail_count
        for i, target_uid in enumerate(all_users):
            try:
                if message.content_type == 'text':
                    bot.send_message(target_uid, message.text)
                elif message.content_type == 'photo':
                    bot.send_photo(target_uid, message.photo[-1].file_id,
                                   caption=message.caption or "")
                elif message.content_type == 'video':
                    bot.send_video(target_uid, message.video.file_id,
                                   caption=message.caption or "")
                elif message.content_type == 'document':
                    bot.send_document(target_uid, message.document.file_id,
                                      caption=message.caption or "")
                elif message.content_type == 'animation':
                    bot.send_animation(target_uid, message.animation.file_id,
                                       caption=message.caption or "")
                elif message.content_type == 'sticker':
                    bot.send_sticker(target_uid, message.sticker.file_id)
                sent_count += 1
            except Exception:
                fail_count += 1
            if (i + 1) % 50 == 0:
                try:
                    bot.edit_message_text(
                        f"📣 Yuborilmoqda...\n"
                        f"✅ Yuborildi: {sent_count}\n"
                        f"❌ Xatolik: {fail_count}\n"
                        f"📊 Qoldi: {total - i - 1}",
                        admin_uid, prog_msg.message_id
                    )
                except:
                    pass
            time.sleep(0.03)

        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO broadcasts (text, sent_count, fail_count, admin_id) VALUES (?,?,?,?)",
                  (str(message.text or message.content_type), sent_count, fail_count, admin_uid))
        conn.commit()
        conn.close()

        try:
            bot.edit_message_text(
                f"✅ BROADCAST TUGADI!\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"👥 Jami: {total}\n"
                f"✅ Yuborildi: {sent_count}\n"
                f"❌ Xatolik: {fail_count}\n"
                f"⏰ {datetime.now().strftime('%H:%M:%S')}",
                admin_uid, prog_msg.message_id
            )
        except:
            bot.send_message(admin_uid,
                f"✅ Broadcast tugadi! Yuborildi: {sent_count}, Xatolik: {fail_count}"
            )

    threading.Thread(target=do_broadcast, daemon=True).start()

# ─────────────────────────────────────────────────────────────
#  🚀  BOTNI ISHGA TUSHIRISH
# ─────────────────────────────────────────────────────────────
def main():
    print("╔══════════════════════════════════════════════════╗")
    print("║        🤖 VSF AI PHOTO BOT — PREMIUM            ║")
    print(f"║        Versiya: {BOT_VERSION}                         ║")
    print(f"║        Muallif: {AUTHOR}                      ║")
    print("╚══════════════════════════════════════════════════╝")

    init_db()
    print("✅ Ma'lumotlar bazasi ishga tushirildi")

    # Render.com uchun serverni ishga tushirish (yangi qo'shilgan qism)
    threading.Thread(target=run_dummy_server, daemon=True).start()

    channels = get_channels()
    print(f"📢 Faol kanallar: {len(channels)}")
    for ch, title in channels:
        print(f"   • {ch} — {title}")

    print(f"🎨 Stillar soni  : {len(STYLES)}")
    print(f"📐 Nisbatlar soni: {len(ASPECTS)}")
    print(f"🛡 Admin ID(lar) : {ADMIN_IDS}")
    print()
    print("🟢 Bot ishga tushdi! Polling boshlandi...\n")

    bot.infinity_polling(
        timeout=60,
        long_polling_timeout=60,
        allowed_updates=["message", "callback_query"]
    )

if __name__ == "__main__":
    main()