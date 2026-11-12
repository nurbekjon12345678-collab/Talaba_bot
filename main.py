import telebot
from telebot import types
import sqlite3
import os
import re
import g4f
import requests
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

try:
    from docx import Document
    WORD_AVAILABLE = True
except ImportError:
    WORD_AVAILABLE = False

TOKEN = "9204315206:AAHcHQDoCP1L7PNxCf_r4LedwkHbUIiyLnE"
REQUIRED_CHANNEL = "@talaba_guruh1"
REQUIRED_GROUP = "@talaba_guruh1"
ADMIN_ID = 8161543250

bot = telebot.TeleBot(TOKEN)
user_orders = {}

def register_unicode_font():
    font_paths = [
        "/system/fonts/Roboto-Regular.ttf",
        "/system/fonts/DroidSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for path in font_paths:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont('CustomFont', path))
            return 'CustomFont'
    return 'Helvetica'

PDF_FONT = register_unicode_font()

def init_db():
    conn = sqlite3.connect('students_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            used_count INTEGER DEFAULT 0,
            invited_by INTEGER,
            invite_count INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def check_sub(user_id):
    if user_id == ADMIN_ID:
        return True
    try:
        ch = bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        gr = bot.get_chat_member(REQUIRED_GROUP, user_id)
        statuses = ['creator', 'administrator', 'member']
        return ch.status in statuses and gr.status in statuses
    except Exception:
        return True

def clean_text_for_pdf(text):
    if "<html" in text.lower() or "<doctype" in text.lower():
        text = re.sub(r'<.*?>', '', text)
    
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        l_lower = line.lower()
        if any(w in l_lower for w in ["i will now", "your slide", "feel free", "here is", "http://", "https://", "generate", "в такие вопросы", "```html", "```"]):
            continue
        cleaned_line = line.replace("**", "").replace("*", "").replace("###", "").replace("##", "").replace("#", "")
        cleaned_line = cleaned_line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if cleaned_line.strip():
            cleaned_lines.append(cleaned_line.strip())
    return "\n".join(cleaned_lines)

# Kafolatlangan va har qanday mavzuga moslashuvchi professional ilmiy diagramma/sxema
def create_topic_drawing(title_text, topic_name):
    d = Drawing(400, 160)
    d.add(Rect(0, 0, 400, 160, fillColor=colors.HexColor('#f8fafc'), strokeColor=colors.HexColor('#cbd5e1'), strokeWidth=1, rx=8, ry=8))
    
    d.add(Rect(20, 120, 360, 25, fillColor=colors.HexColor('#1a365d'), strokeColor=None, rx=4, ry=4))
    d.add(String(25, 127, f"Sxema: {topic_name[:35]}", fontName=PDF_FONT, fontSize=11, fillColor=colors.white))
    
    d.add(Rect(30, 40, 90, 50, fillColor=colors.HexColor('#e2e8f0'), strokeColor=colors.HexColor('#64748b'), rx=4, ry=4))
    d.add(String(42, 62, "1-Bosqich", fontName=PDF_FONT, fontSize=10, fillColor=colors.HexColor('#1e293b')))
    
    d.add(Line(120, 65, 155, 65, strokeColor=colors.HexColor('#1a365d'), strokeWidth=2))
    
    d.add(Rect(155, 40, 90, 50, fillColor=colors.HexColor('#bfdbfe'), strokeColor=colors.HexColor('#3b82f6'), rx=4, ry=4))
    d.add(String(167, 62, "Amaliyot", fontName=PDF_FONT, fontSize=10, fillColor=colors.HexColor('#1e395b')))
    
    d.add(Line(245, 65, 280, 65, strokeColor=colors.HexColor('#1a365d'), strokeWidth=2))
    
    d.add(Rect(280, 40, 90, 50, fillColor=colors.HexColor('#bbf7d0'), strokeColor=colors.HexColor('#22c55e'), rx=4, ry=4))
    d.add(String(295, 62, "Xulosa", fontName=PDF_FONT, fontSize=10, fillColor=colors.HexColor('#166534')))
    
    return d

def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📝 Referat buyurtma berish"), types.KeyboardButton("📊 Slayd buyurtma berish"))
    markup.add(types.KeyboardButton("📚 Kurs ishi buyurtma berish"), types.KeyboardButton("✏️ Insho / Esse buyurtma berish"))
    markup.add(types.KeyboardButton("📝 Mustaqil ish buyurtma berish"))
    if user_id == ADMIN_ID:
        markup.add(types.KeyboardButton("👑 Admin Panel"))
    return markup

def language_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("🇺🇿 O'zbek tili"), types.KeyboardButton("🇷🇺 Rus tili (Русский)"), types.KeyboardButton("🇺🇸 Ingliz tili (English)"))
    return markup

def size_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📄 Kichik (3-5 varoq)"), types.KeyboardButton("📑 O'rtacha (6-10 varoq)"), types.KeyboardButton("📚 Katta (11-15 varoq)"))
    return markup

def format_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📄 PDF (Printer uchun)"), types.KeyboardButton("📝 Word (.docx)"))
    return markup

def ask_ai(prompt, lang_name):
    full_prompt = (
        f"MUHIM: Faqat va faqat {lang_name} tilida yoz. "
        f"Hech qanday HTML kod, inglizcha kirish yoki xulosa so'zlarini ishlatma. "
        f"Mavzu bo'yicha juda uzun, chuqur ilmiy va batafsil matn yoz.\n\n" + prompt
    )
    for model_name in [g4f.models.gemini, g4f.models.gpt_4o]:
        try:
            response = g4f.ChatCompletion.create(
                model=model_name,
                messages=[{"role": "user", "content": full_prompt}]
            )
            if response and len(response) > 100:
                return response
        except Exception:
            continue
    return "Ma'lumot tayyorlashda xatolik yuz berdi."

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "NoName"
    
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    conn = sqlite3.connect('students_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, username, invited_by) VALUES (?, ?, ?)", (user_id, username, referrer_id))
        if referrer_id and referrer_id != user_id:
            cursor.execute("UPDATE users SET invite_count = invite_count + 1 WHERE user_id = ?", (referrer_id,))
            try:
                bot.send_message(referrer_id, "🎉 Yangi do'stingiz sizning havolangiz orqali botga qo'shildi!")
            except Exception:
                pass
        conn.commit()
    conn.close()
    
    bot.send_message(message.chat.id, "🤖 **Talaba Bot xizmatingizga tayyor!**\n\nKerakli xizmat turini tanlang:", reply_markup=main_menu(user_id), parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    user_id = message.from_user.id
    
    if message.text == "👑 Admin Panel" and user_id == ADMIN_ID:
        conn = sqlite3.connect('students_bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        conn.close()
        bot.send_message(message.chat.id, f"👑 **Admin Panel**\n\nBotdagi jami foydalanuvchilar soni: **{total_users} ta**", parse_mode="Markdown")
        return

    services = {
        "📝 Referat buyurtma berish": "referat",
        "📊 Slayd buyurtma berish": "slayd",
        "📚 Kurs ishi buyurtma berish": "kurs ishi",
        "✏️ Insho / Esse buyurtma berish": "insho",
        "📝 Mustaqil ish buyurtma berish": "mustaqil ish"
    }

    if message.text in services:
        conn = sqlite3.connect('students_bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT used_count, invite_count FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()
        conn.close()
        
        used_count = user_data[0] if user_data else 0
        invites = user_data[1] if user_data else 0
        
        if user_id != ADMIN_ID and used_count >= 1:
            is_sub = check_sub(user_id)
            if not is_sub or invites < 3:
                bot_info = bot.get_me()
                ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("📣 Kanal va guruhga a'zo bo'lish", url=f"https://t.me/{REQUIRED_CHANNEL.lstrip('@')}"))
                
                err = (f"🔒 **Bepul 1 ta ishlash limitingiz tugadi!**\n\n"
                       f"Davom etish uchun quyidagi shartlarni bajaring:\n"
                       f"1️⃣ Kanal va guruhimizga a'zo bo'ling.\n"
                       f"2️⃣ Kamida **3 ta do'stingizni** taklif qiling (Sizda: {invites}/3 ta).\n\n"
                       f"🔗 Sizning taklif havolangiz:\n`{ref_link}`")
                bot.send_message(message.chat.id, err, reply_markup=markup, parse_mode="Markdown")
                return

        user_orders[user_id] = {"type": services[message.text]}
        bot.send_message(message.chat.id, "Ish qaysi tilda tayyorlansin?", reply_markup=language_menu())
        bot.register_next_step_handler(message, set_language)

def set_language(message):
    user_id = message.from_user.id
    if user_id not in user_orders:
        return
    if "Rus" in message.text:
        user_orders[user_id]["lang"] = "rus"
        user_orders[user_id]["lang_name"] = "Russian"
    elif "Ingliz" in message.text:
        user_orders[user_id]["lang"] = "ingliz"
        user_orders[user_id]["lang_name"] = "English"
    else:
        user_orders[user_id]["lang"] = "ozbek"
        user_orders[user_id]["lang_name"] = "Uzbek"

    bot.send_message(message.chat.id, "Ish hajmini tanlang:", reply_markup=size_menu())
    bot.register_next_step_handler(message, set_size)

def set_size(message):
    user_id = message.from_user.id
    if user_id not in user_orders:
        return
    user_orders[user_id]["size"] = message.text

    bot.send_message(message.chat.id, "Hujjat qaysi formatda bo'lsin?", reply_markup=format_menu())
    bot.register_next_step_handler(message, set_format)

def set_format(message):
    user_id = message.from_user.id
    if user_id not in user_orders:
        return
    user_orders[user_id]["format"] = "word" if "Word" in message.text else "pdf"

    bot.send_message(message.chat.id, "Endi ishning **mavzusini** kiriting (masalan: *Kvant fizikasi asoslari*):", reply_markup=types.ReplyKeyboardRemove(), parse_mode="Markdown")
    bot.register_next_step_handler(message, ask_image_choice)

def ask_image_choice(message):
    user_id = message.from_user.id
    if user_id not in user_orders:
        return
    user_orders[user_id]["topic"] = message.text

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🖼 Ha, sxemalar bilan", callback_data="img_yes"),
        types.InlineKeyboardButton("📄 Yo'q, faqat matn", callback_data="img_no")
    )
    bot.send_message(message.chat.id, "Hujjatga mavzuga mos ilmiy sxemalar qo'shilsinmi?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("img_"))
def callback_image_choice(call):
    user_id = call.from_user.id
    if user_id not in user_orders:
        bot.answer_callback_query(call.id, "Xatolik yuz berdi. /start buyrug'ini bosing.")
        return

    user_orders[user_id]["with_images"] = (call.data == "img_yes")
    bot.answer_callback_query(call.id, "Qabul qilindi!")
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    generate_document_final(call.message, user_id)

def generate_document_final(message, user_id):
    if user_id not in user_orders:
        return
    
    order_info = user_orders[user_id]
    topic = order_info["topic"]
    lang_name = order_info["lang_name"]
    doc_type = order_info["type"]
    with_images = order_info["with_images"]
    doc_format = order_info.get("format", "pdf")

    wait_msg = bot.send_message(message.chat.id, "⏳ A4 printer uchun hujjat tayyorlanmoqda, iltimos kuting...")

    intro = ask_ai(f"Write a very long academic Introduction (Kirish) for the {doc_type} about: '{topic}'.", lang_name)
    ch1 = ask_ai(f"Write Chapter 1 (1-Bob) with detailed subheadings about: '{topic}'.", lang_name)
    ch2 = ask_ai(f"Write Chapter 2 (2-Bob) with detailed subheadings about: '{topic}'.", lang_name)
    ch3 = ask_ai(f"Write Chapter 3 (3-Bob) about: '{topic}'.", lang_name)
    conclusion = ask_ai(f"Write a comprehensive academic Conclusion (Xulosa) for the {doc_type} about: '{topic}'.", lang_name)

    sections = [
        ("KIRISH", intro),
        ("1-BOB. NAZARIY ASOSLARI", ch1),
        ("2-BOB. TAHLIL VA AMALIY AHAMIYATI", ch2),
        ("3-BOB. ISTIQBOLLARI VA RIVOJLANISHI", ch3),
        ("XULOSA", conclusion)
    ]

    if doc_format == "word":
        if not WORD_AVAILABLE:
            bot.send_message(message.chat.id, "⚠️ Serverda python-docx moduli o'rnatilmagani uchun hujjat PDF formatida yaratildi.")
            doc_format = "pdf"
        else:
            file_name = f"{user_id}_document.docx"
            doc = Document()
            doc.add_heading(f"Mavzu: {topic}", level=0)
            
            for title, text in sections:
                doc.add_heading(title, level=1)
                cleaned = clean_text_for_pdf(text)
                for p in cleaned.split('\n'):
                    if p.strip():
                        doc.add_paragraph(p)
                if with_images:
                    doc.add_paragraph(f"[Mavzu sxemasi: {topic}]")
                doc.add_page_break()
            doc.save(file_name)

    if doc_format == "pdf":
        file_name = f"{user_id}_document.pdf"
        doc = SimpleDocTemplate(
            file_name, 
            pagesize=A4,
            leftMargin=56, rightMargin=56,
            topMargin=56, bottomMargin=56
        )

        styles = ParagraphStyle(
            'Normal',
            fontName=PDF_FONT,
            fontSize=12,
            leading=18,
            textColor=colors.HexColor('#222222')
        )
        
        title_style = ParagraphStyle(
            'TitleStyle',
            fontName=PDF_FONT,
            fontSize=18,
            leading=24,
            alignment=1,
            textColor=colors.HexColor('#1a365d')
        )

        section_heading_style = ParagraphStyle(
            'HeadingStyle',
            fontName=PDF_FONT,
            fontSize=14,
            leading=18,
            textColor=colors.HexColor('#1a365d'),
            spaceBefore=15,
            spaceAfter=10
        )

        story = []
        story.append(Paragraph(f"<b>Mavzu: {topic}</b>", title_style))
        story.append(Spacer(1, 20))

        for title, text in sections:
            story.append(Paragraph(title, section_heading_style))
            story.append(Spacer(1, 5))
            
            cleaned = clean_text_for_pdf(text)
            for p in cleaned.split('\n'):
                if p.strip():
                    story.append(Paragraph(p, styles))
                    story.append(Spacer(1, 8))
            
            if with_images:
                story.append(Spacer(1, 10))
                story.append(create_topic_drawing(title, topic))
                story.append(Spacer(1, 10))
            
            story.append(PageBreak())

        doc.build(story)

    conn = sqlite3.connect('students_bot.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET used_count = used_count + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    try:
        with open(file_name, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=f"✅ Sizning **{topic}** mavzusidagi ishingiz tayyor!", parse_mode="Markdown")
        bot.delete_message(message.chat.id, wait_msg.message_id)
    except Exception as e:
        bot.send_message(message.chat.id, f"Faylni yuborishda xatolik yuz berdi: {e}")

    if os.path.exists(file_name):
        os.remove(file_name)
            
    if user_id in user_orders:
        del user_orders[user_id]
        
    bot.send_message(message.chat.id, "Yana xizmat turini tanlashingiz mumkin:", reply_markup=main_menu(user_id))

if __name__ == '__main__':
    print("Bot ishga tushdi...")
    bot.infinity_polling()
