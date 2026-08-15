"""
╔══════════════════════════════════════════════════════════════╗
║     Kairozen Bot — 🎮 Multi-Games + RTP Control (Full Code)   ║
║     Full Fixed: Built-in KHQR Generator + Flask Web Server    ║
╚══════════════════════════════════════════════════════════════╝
"""

import json, logging, time, re, threading, hashlib, io, os, sys, subprocess, random
import requests as http_req
import telebot
from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from flask import Flask
from threading import Thread

# ─── Auto-install deps ───
def _ensure_deps():
    pkgs = {"PIL": "pillow", "qrcode": "qrcode", "flask": "flask"}
    for mod, pkg in pkgs.items():
        try: __import__(mod)
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", pkg,
                            "--break-system-packages", "-q"], check=False)
_ensure_deps()

import qrcode
from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
#  FLASK SERVER FOR RENDER (PORT BINDING)
# ═══════════════════════════════════════════════════════════
web_app = Flask('')

@web_app.route('/')
def home():
    return "Bot is running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# ═══════════════════════════════════════════════════════════
#  CONFIG — ព័ត៌មានគណនី
# ═══════════════════════════════════════════════════════════
BOT_TOKEN          
DEPOSIT_EXPIRE_SEC = 180   # 3 minutes
POLL_INTERVAL      = 5

MIN_BET            = 0.10  # ថ្លៃចាក់អប្បបរមា ($0.10)
MAX_BET            = 50.0  # ថ្លៃចាក់អតិបរមា ($50.00)

# ═══════════════════════════════════════════════════════════
#  FILES & SETTINGS
# ═══════════════════════════════════════════════════════════
WALLETS_FILE    = "aio_wallets.json"
USERS_FILE      = "aio_users.json"
LANG_FILE       = "aio_lang.json"
PROMO_FILE      = "aio_promos.json"
STORE_DEP_FILE  = "aio_store_deposits.json"
BETS_FILE       = "aio_user_bets.json"
SETTINGS_FILE   = "aio_settings.json"

def _load(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return default

def _save(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e: logger.error(f"Save {path}: {e}")

# ─── Load state ───
wallets      = _load(WALLETS_FILE,   {})
users_db     = _load(USERS_FILE,     {})
user_lang    = _load(LANG_FILE,      {})
promos       = _load(PROMO_FILE,     {})
store_deps   = _load(STORE_DEP_FILE, {})
user_bets    = _load(BETS_FILE,      {})
settings     = _load(SETTINGS_FILE,  {"win_rate": 30})

waiting      = {}

# ═══════════════════════════════════════════════════════════
#  BOT & HELPERS
# ═══════════════════════════════════════════════════════════
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

def _make_session():
    s = http_req.Session()
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    r = Retry(total=3, backoff_factor=2, status_forcelist=[500,502,503,504])
    a = HTTPAdapter(max_retries=r)
    s.mount("http://", a); s.mount("https://", a)
    return s
http = _make_session()

# ─── Language Strings ───
STRINGS = {
    "kh": {
        "welcome": (
            "👋 សូស្ដីមក <b>Kairozen カイロゼン</b>!\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🎮 ស្វាគមន៍មកកាន់មជ្ឈមណ្ឌលហ្គេម\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💰 សាច់ប្រាក់: <b>${:.2f}</b>"
        ),
        "select_lang":   "🌐 ជ្រើសរើសភាសា:",
        "lang_set":      "✅ ភាសាត្រូវបានផ្លាស់ប្ដូរ!",
        "menu":          "🏠 ត្រឡប់ Menu ដើម",
        "banned":        "🚫 គណនីរបស់អ្នកត្រូវបាន ban!",
        "cancel_ok":     "🏠 Menu",
        "support_msg": (
            "💬 <b>ជំនួយ</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "📞 Admin: @FaFaKN1688\n"
            "🌐 Channel: https://t.me/FaFaKN168"
        ),
        "fallback": "❓ ប្រើ Menu ខាងក្រោម",
    },
    "en": {
        "welcome": (
            "👋 Welcome to <b>Kairozen カイロゼン</b>!\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🎮 Welcome to Game Center\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💰 Balance: <b>${:.2f}</b>"
        ),
        "select_lang":   "🌐 Select Language:",
        "lang_set":      "✅ Language changed!",
        "menu":          "🏠 Back to Menu",
        "banned":        "🚫 Your account has been banned!",
        "cancel_ok":     "🏠 Menu",
        "support_msg": (
            "💬 <b>Support</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "📞 Admin: @FaFaKN1688\n"
            "🌐 Channel: https://t.me/FaFaKN168"
        ),
        "fallback": "❓ Use the menu below",
    },
}

def get_lang(uid): return user_lang.get(str(uid), "kh")

def t(uid, key, *args):
    lang = get_lang(uid)
    s = STRINGS.get(lang, STRINGS["kh"]).get(key) or STRINGS["kh"].get(key, key)
    if args:
        try: return s.format(*args)
        except: return s
    return s

def bal(uid): return float(wallets.get(str(uid), 0))

def add_bal(uid, amt):
    wallets[str(uid)] = round(bal(uid) + amt, 2)
    _save(WALLETS_FILE, wallets)

def ded_bal(uid, amt):
    wallets[str(uid)] = max(0, round(bal(uid) - amt, 2))
    _save(WALLETS_FILE, wallets)

def get_user_bet(uid):
    return float(user_bets.get(str(uid), 0.50))

def set_user_bet(uid, amt):
    amt = max(MIN_BET, min(MAX_BET, round(amt, 2)))
    user_bets[str(uid)] = amt
    _save(BETS_FILE, user_bets)

def get_win_rate():
    return int(settings.get("win_rate", 30))

def set_win_rate(rate):
    settings["win_rate"] = int(rate)
    _save(SETTINGS_FILE, settings)

def should_win():
    rate = get_win_rate()
    return random.randint(1, 100) <= rate

# ═══════════════════════════════════════════════════════════
#  PROMO CODE HELPERS
# ═══════════════════════════════════════════════════════════
def apply_promo(uid, code, amount):
    code = code.strip().upper()
    p = promos.get(code)
    if not p: return amount, 0, "❌ Promo Code ខុស!"
    if p.get("uses", 0) > 0 and p.get("used", 0) >= p["uses"]:
        return amount, 0, "❌ Promo Code ផុតសិទ្ធហើយ!"
    user_used = p.get("user_used", {})
    if str(uid) in user_used:
        return amount, 0, "❌ អ្នកបានប្រើ Promo Code នេះហើយ!"
    if p.get("pct", False):
        discount = round(amount * float(p["discount"]) / 100, 2)
    else:
        discount = min(float(p["discount"]), amount)
    final = max(0, round(amount - discount, 2))
    return final, discount, None

def confirm_promo(code, uid):
    code = code.strip().upper()
    p = promos.get(code)
    if not p: return
    p["used"] = p.get("used", 0) + 1
    uu = p.get("user_used", {})
    uu[str(uid)] = 1
    p["user_used"] = uu
    _save(PROMO_FILE, promos)

# ═══════════════════════════════════════════════════════════
#  KEYBOARDS
# ═══════════════════════════════════════════════════════════
def main_kb(uid=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🎰 ស្លុត", "🎲 ឡុកឡាក់ (តូច/ធំ)")
    kb.row("🎯 បាញ់ស៊ីប", "🏀 បោះបាល់", "⚽ ទាត់បាល់")
    kb.row("🎳 ប៊ូលីង")
    kb.row("⚙️ កំណត់ថ្លៃចាក់", "💰 ដាក់ប្រាក់", "💸 ដកប្រាក់")
    kb.row("👜 កាបូបលុយ", "💬 Support")
    return kb

def admin_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🎛️ កំណត់អត្រាឈ្នះ", "💰 កាបូបលុយ")
    kb.row("💸 បន្ថែមប្រាក់", "💔 កាត់ប្រាក់")
    kb.row("👥 អ្នកប្រើប្រាស់", "🎟️ លេខកូដPromo", "📢 ផ្សព្វផ្សាយ")
    return kb

def cancel_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("✕ Cancel")
    return kb

def lang_select_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇰🇭 ខ្មែរ", callback_data="setlang:kh"),
         InlineKeyboardButton("🇬🇧 English", callback_data="setlang:en")]
    ])

def win_rate_kb():
    rate = get_win_rate()
    rates = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    btns, row = [], []
    for r in rates:
        mark = " ✅" if r == rate else ""
        row.append(InlineKeyboardButton(f"{r}%{mark}", callback_data=f"setrate:{r}"))
        if len(row) == 3:
            btns.append(row); row = []
    if row: btns.append(row)
    return InlineKeyboardMarkup(btns)

def bet_selection_kb(uid):
    cur_bet = get_user_bet(uid)
    presets = [0.10, 0.50, 1.00, 2.00, 5.00, 10.00, 20.00, 50.00]
    btns, row = [], []
    for b in presets:
        mark = " ✅" if b == cur_bet else ""
        row.append(InlineKeyboardButton(f"${b:.2f}{mark}", callback_data=f"setbet:{b}"))
        if len(row) == 4:
            btns.append(row); row = []
    if row: btns.append(row)
    btns.append([InlineKeyboardButton("✏️ វាយបញ្ចូលចំនួនផ្ទាល់ខ្លួន", callback_data="setbet:custom")])
    return InlineKeyboardMarkup(btns)

def dice_choice_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔹 ចាក់ តូច (1, 2, 3)", callback_data="diceplay:small"),
         InlineKeyboardButton("🔸 ចាក់ ធំ (4, 5, 6)", callback_data="diceplay:big")]
    ])

def deposit_amt_kb(uid=None, promo_code=None):
    lang = get_lang(uid) if uid else "kh"
    amts = [1, 2, 5, 10, 20, 50]
    btns, row = [], []
    for a in amts:
        row.append(InlineKeyboardButton(f"${a}", callback_data=f"dep:{a}"))
        if len(row) == 3:
            btns.append(row); row = []
    if row: btns.append(row)
    btns.append([InlineKeyboardButton("✏️ ផ្ទាល់ខ្លួន" if lang=="kh" else "✏️ Custom", callback_data="dep:custom")])
    if promo_code:
        btns.append([InlineKeyboardButton(f"🎟️ Promo: {promo_code} ✅", callback_data="dep:clrpromo")])
    else:
        btns.append([InlineKeyboardButton("🎟️ ដាក់ Promo Code" if lang=="kh" else "🎟️ Enter Promo Code", callback_data="dep:promo")])
    return InlineKeyboardMarkup(btns)

def _show_promos(uid):
    if not promos:
        bot.send_message(uid, "❌ គ្មាន Promo Code ទេ", reply_markup=admin_kb()); return
    lines = ["🎟️ <b>Promo Codes</b>\n━━━━━━━━━━━━━━━━━━"]
    btns  = []
    for code, p in promos.items():
        dtype = f"{p['discount']}%" if p.get("pct") else f"${p['discount']}"
        uses  = f"{p.get('used',0)}/{p.get('uses',0)}"
        lines.append(f"• <code>{code}</code> — <b>{dtype}</b> | {uses} ប្រើ")
        btns.append([InlineKeyboardButton(f"🗑 {code}", callback_data=f"adminpromo:del_{code}")])
    btns.append([InlineKeyboardButton("➕ Add Promo", callback_data="adminpromo:add")])
    bot.send_message(uid, "\n".join(lines), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns))

# ═══════════════════════════════════════════════════════════
#  PURE PYTHON KHQR GENERATOR & DEPOSIT PROCESS
# ═══════════════════════════════════════════════════════════
def _crc16_ccitt(data: str) -> str:
    crc = 0xFFFF
    for ch in data:
        crc = (crc ^ (ord(ch) << 8)) & 0xFFFF
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"

def _generate_khqr(uid, amount, note=""):
    try:
        amt_str = f"{float(amount):.2f}"
        tag_00 = "000201"
        tag_01 = "010212"
        
        # Tag 29 - Merchant Account Info
        sub_tag_00 = f"0016{BANK_ACCOUNT}"
        tag_29 = f"29{len(sub_tag_00):02d}{sub_tag_00}"
        
        tag_52 = "52045999"
        tag_53 = "5303840"  # USD
        tag_54 = f"54{len(amt_str):02d}{amt_str}"
        tag_58 = "5802KH"
        tag_59 = f"59{len(MERCHANT_NAME):02d}{MERCHANT_NAME}"
        tag_60 = f"60{len(MERCHANT_CITY):02d}{MERCHANT_CITY}"
        
        bill = f"uid{uid}"[:25]
        sub_tag_01 = f"01{len(bill):02d}{bill}"
        tag_62 = f"62{len(sub_tag_01):02d}{sub_tag_01}"
        
        raw_data = tag_00 + tag_01 + tag_29 + tag_52 + tag_53 + tag_54 + tag_58 + tag_59 + tag_60 + tag_62 + "6304"
        crc = _crc16_ccitt(raw_data)
        return raw_data + crc
    except Exception as e:
        logger.error(f"Generate KHQR String error: {e}")
        return ""

def _check_bakong(md5, amount, start_ts):
    # កន្លែងពិនិត្យវិក្កយបត្រ (បើគ្មាន Bakong API Key វានឹងរង់ចាំ Admin អនុម័ត)
    return False

def _watch_deposit(uid, uid_str, dep_id, amount, start_ts):
    deadline = time.time() + DEPOSIT_EXPIRE_SEC + 60
    while time.time() < deadline:
        dep = store_deps.get(dep_id)
        if not dep or dep.get("status") != "pending": return
        md5 = dep.get("md5", "")
        if _check_bakong(md5, amount, start_ts):
            bonus = float(dep.get("bonus", 0))
            total_credit = round(amount + bonus, 2)
            add_bal(uid, total_credit)
            store_deps[dep_id]["status"] = "confirmed"
            _save(STORE_DEP_FILE, store_deps)
            new_b = bal(uid)
            msg = (f"✅ <b>ដាក់លុយបានជោគជ័យ!</b>\n"
                   f"━━━━━━━━━━━━━━━━━━\n"
                   f"💰 បញ្ញើ: <b>${amount:.2f}</b>")
            if bonus > 0: msg += f"\n🎟️ Promo Bonus: <b>+${bonus:.2f}</b>"
            msg += (f"\n💳 Balance: <b>${new_b:.2f}</b>")
            try: bot.send_message(uid, msg, parse_mode="HTML", reply_markup=main_kb(uid))
            except: pass
            try:
                bot.send_message(ADMIN_ID,
                    f"💰 <b>ដាក់លុយ ✅</b>\n👤 <code>{uid_str}</code>\n"
                    f"💰 ${amount:.2f}" + (f" + Bonus ${bonus:.2f}" if bonus>0 else ""),
                    parse_mode="HTML")
            except: pass
            return
        time.sleep(POLL_INTERVAL)
    dep = store_deps.get(dep_id)
    if dep and dep.get("status") == "pending":
        dep["status"] = "expired"; _save(STORE_DEP_FILE, store_deps)
        try: bot.send_message(uid, "⏰ <b>QR ផុតកំណត់!</b> សូមចុច Top Up ម្ដងទៀត", parse_mode="HTML")
        except: pass

def _send_deposit_qr(uid, amount, promo_code=None, label="💸 ដាក់លុយ", bonus=0.0, promo_code_name=None):
    uid_str = str(uid)
    final_amount = amount
    discount = 0
    promo_applied = promo_code_name
    if promo_code and not promo_applied:
        fa, dc, err = apply_promo(uid, promo_code, amount)
        if not err:
            final_amount = fa; discount = dc; promo_applied = promo_code

    qr_str = _generate_khqr(uid, final_amount, f"uid={uid}")
    if not qr_str:
        bot.send_message(uid, "⚠️ មានបញ្ហា Generate QR! សូមទំនាក់ទំនង Admin", parse_mode="HTML")
        return

    md5_hash = hashlib.md5(qr_str.encode()).hexdigest()

    dep_id   = f"dep_{uid}_{int(time.time())}"
    start_ts = int(time.time())
    store_deps[dep_id] = {
        "uid": uid_str, "amount": final_amount, "status": "pending",
        "bonus": bonus, "promo": promo_applied or "",
        "md5": md5_hash, "qr_str": qr_str,
    }
    _save(STORE_DEP_FILE, store_deps)

    cap = (f"{label}\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"💰 ចំនួន: <b>${final_amount:.2f}</b>\n"
           f"🏦 គណនី: <code>{BANK_ACCOUNT}</code>")
    if bonus > 0: cap += f"\n🎟️ Bonus: <b>+${bonus:.2f}</b>"
    elif discount > 0: cap += f"\n🎟️ Promo: <b>-${discount:.2f}</b> ({promo_applied})"
    cap += (f"\n⏱ ផុតកំណត់: <b>{DEPOSIT_EXPIRE_SEC//60} នាទី</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📱 Scan ជាមួយ Bakong / ABA / Wing\n"
            f"📌 <i>ផ្ទេររួចផ្ញើ Slip មកទីនេះដើម្បីបញ្ចូលលុយ</i>")
    if promo_applied and (bonus > 0 or discount > 0):
        confirm_promo(promo_applied, uid)

    # បង្កើតរូបភាព QR Code
    img_buf = io.BytesIO()
    try:
        qr = qrcode.QRCode(box_size=8, border=2)
        qr.add_data(qr_str)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        img.save(img_buf, format="PNG")
        img_buf.seek(0)
    except Exception as e:
        logger.error(f"Generate QR Image error: {e}")
        img_buf = None

    if img_buf:
        try:
            bot.send_photo(uid, img_buf, caption=cap, parse_mode="HTML")
        except Exception:
            bot.send_message(uid, cap, parse_mode="HTML")
    else:
        bot.send_message(uid, cap, parse_mode="HTML")
        
    threading.Thread(target=_watch_deposit, args=(uid, uid_str, dep_id, final_amount, start_ts), daemon=True).start()

# ═══════════════════════════════════════════════════════════
#  TRACK USER & START
# ═══════════════════════════════════════════════════════════
def _track_user(message):
    uid = message.chat.id
    uid_str = str(uid)
    u = message.from_user
    users_db[uid_str] = {
        "name":     u.first_name or "",
        "username": u.username or "",
        "last":     int(time.time()),
        "banned":   users_db.get(uid_str, {}).get("banned", False),
    }
    _save(USERS_FILE, users_db)
    wallets.setdefault(uid_str, 0.0)

def is_banned(uid): return bool(users_db.get(str(uid), {}).get("banned", False))

@bot.message_handler(commands=["start"])
def cmd_start(message):
    uid = message.chat.id
    waiting.pop(uid, None)
    _track_user(message)
    if is_banned(uid): bot.send_message(uid, t(uid, "banned")); return
    if uid == ADMIN_ID:
        rate = get_win_rate()
        bot.send_message(uid,
            f"🤖 <b>Panel Admin — Kairozen Bot</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <code>{ADMIN_ID}</code>\n"
            f"🎯 អត្រាឈ្នះបច្ចុប្បន្ន (RTP): <b>{rate}%</b>\n"
            f"━━━━━━━━━━━━━━━━━━",
            parse_mode="HTML", reply_markup=admin_kb())
        return
    if str(uid) not in user_lang:
        bot.send_message(uid, "🌐 <b>ជ្រើសរើសភាសា / Select Language</b>", parse_mode="HTML", reply_markup=lang_select_kb())
        return
    _show_welcome(uid)

def _show_welcome(uid):
    bot.send_message(uid, t(uid, "welcome", bal(uid)), parse_mode="HTML", reply_markup=main_kb(uid))

# ═══════════════════════════════════════════════════════════
#  CALLBACK QUERIES
# ═══════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda c: c.data.startswith("setlang:"))
def cb_setlang(call):
    uid = call.message.chat.id
    lang = call.data.split(":")[1]
    user_lang[str(uid)] = lang
    _save(LANG_FILE, user_lang)
    bot.answer_callback_query(call.id, t(uid, "lang_set"))
    try: bot.delete_message(uid, call.message.message_id)
    except: pass
    _show_welcome(uid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("setrate:"))
def cb_setrate(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID: return
    rate = int(call.data.split(":")[1])
    set_win_rate(rate)
    bot.answer_callback_query(call.id, f"✅ បានប្ដូរអត្រាឈ្នះទៅ {rate}%")
    try:
        bot.edit_message_text(
            f"🎛️ <b>កំណត់អត្រាឈ្នះ (RTP)</b>\n━━━━━━━━━━━━━━━━━━\n"
            f"បានកំណត់អត្រាឈ្នះសរុបទៅ៖ <b>{rate}%</b>\n"
            f"<i>(ឱកាសឈ្នះ {rate}% និងចាញ់ {100-rate}%)</i>",
            chat_id=uid, message_id=call.message.message_id, parse_mode="HTML",
            reply_markup=win_rate_kb()
        )
    except: pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("setbet:"))
def cb_setbet(call):
    uid = call.message.chat.id
    val = call.data.split(":")[1]
    bot.answer_callback_query(call.id)
    if val == "custom":
        waiting[uid] = {"step": "custom_bet_amount"}
        bot.send_message(uid, "✏️ <b>សូមផ្ញើចំនួនទឹកប្រាក់ចង់ចាក់ ($0.10 ដល់ $50.00):</b>", parse_mode="HTML", reply_markup=cancel_kb())
        return
    amt = float(val)
    set_user_bet(uid, amt)
    try:
        bot.edit_message_text(
            f"⚙️ <b>បានផ្លាស់ប្ដូរថ្លៃចាក់ទៅ៖ ${amt:.2f}</b>\nជ្រើសរើសហ្គេមខាងក្រោមដើម្បីលេង!",
            chat_id=uid, message_id=call.message.message_id, parse_mode="HTML",
            reply_markup=bet_selection_kb(uid)
        )
    except: pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("diceplay:"))
def cb_diceplay(call):
    uid = call.message.chat.id
    choice = call.data.split(":")[1]
    bot.answer_callback_query(call.id)
    bet = get_user_bet(uid)
    if bal(uid) < bet:
        bot.send_message(uid, f"❌ <b>តុល្យភាពមិនគ្រប់គ្រាន់!</b> ត្រូវការ ${bet:.2f}", parse_mode="HTML"); return

    ded_bal(uid, bet)
    try: bot.delete_message(uid, call.message.message_id)
    except: pass

    msg = bot.send_dice(uid, emoji="🎲")
    time.sleep(2)

    win_result = should_win()
    if win_result:
        val = random.choice([1, 2, 3]) if choice == "small" else random.choice([4, 5, 6])
    else:
        val = random.choice([4, 5, 6]) if choice == "small" else random.choice([1, 2, 3])

    if win_result:
        win_amt = round(bet * 1.95, 2); add_bal(uid, win_amt)
        bot.send_message(uid, f"🎲 <b>ចេញលេខ {val} — អ្នកឈ្នះ!</b>\n💰 ឈ្នះ: <b>+${win_amt:.2f}</b>\n💳 សមតុល្យ: <b>${bal(uid):.2f}</b>", parse_mode="HTML", reply_markup=main_kb(uid))
    else:
        bot.send_message(uid, f"😢 <b>ចេញលេខ {val} — អ្នកចាញ់!</b>\n💸 កាត់: <b>-${bet:.2f}</b>\n💳 សមតុល្យ: <b>${bal(uid):.2f}</b>", parse_mode="HTML", reply_markup=main_kb(uid))

@bot.callback_query_handler(func=lambda c: c.data.startswith("useraction:"))
def cb_useraction(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID: bot.answer_callback_query(call.id); return
    bot.answer_callback_query(call.id)
    parts = call.data.split(":", 2)
    action, target = parts[1], parts[2]

    if action == "ban":
        users_db.setdefault(target, {})["banned"] = True; _save(USERS_FILE, users_db)
        try: bot.edit_message_text(f"🚫 <b>Banned:</b> {users_db[target].get('name','?')} <code>{target}</code>", chat_id=uid, message_id=call.message.message_id, parse_mode="HTML")
        except: pass
    elif action == "unban":
        users_db.setdefault(target, {})["banned"] = False; _save(USERS_FILE, users_db)
        try: bot.edit_message_text(f"🔓 <b>Unbanned:</b> {users_db[target].get('name','?')} <code>{target}</code>", chat_id=uid, message_id=call.message.message_id, parse_mode="HTML")
        except: pass
    elif action == "addbal":
        waiting[uid] = {"step": "add_balance_amt", "target": target}
        bot.send_message(uid, f"💸 <b>បន្ថែម Balance</b> ទៅកាន់ <code>{target}</code>\nផ្ញើចំនួន $:", parse_mode="HTML", reply_markup=cancel_kb())
    elif action == "dedbal":
        waiting[uid] = {"step": "deduct_balance_amt", "target": target}
        bot.send_message(uid, f"💔 <b>កាត់ Balance</b> ពី <code>{target}</code>\nផ្ញើចំនួន $:", parse_mode="HTML", reply_markup=cancel_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("adminpromo:"))
def cb_adminpromo(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID: bot.answer_callback_query(call.id); return
    bot.answer_callback_query(call.id)
    action = call.data.split(":")[1]
    if action == "add":
        waiting[uid] = "promo_add_code"
        bot.send_message(uid, "🎟️ <b>បន្ថែម Promo Code</b>\nផ្ញើ: <code>CODE DISCOUNT TYPE USES</code>\nឧ: <code>SAVE50 50 pct 100</code>", parse_mode="HTML", reply_markup=cancel_kb())
    elif action == "list": _show_promos(uid)
    elif action.startswith("del_"):
        code = action[4:]
        promos.pop(code.upper(), None); _save(PROMO_FILE, promos)
        try: bot.edit_message_text(f"🗑️ Promo <b>{code}</b> លុបហើយ!", chat_id=uid, message_id=call.message.message_id, parse_mode="HTML")
        except: pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("dep:"))
def cb_dep(call):
    uid, uid_str = call.message.chat.id, str(call.message.chat.id)
    val = call.data[4:]
    bot.answer_callback_query(call.id)

    if val == "promo":
        waiting[uid] = {"step": "dep_enter_promo", "msg_id": call.message.message_id}
        bot.send_message(uid, "🎟️ <b>ដាក់ Promo Code:</b>", parse_mode="HTML", reply_markup=cancel_kb()); return
    if val == "clrpromo":
        step = waiting.get(uid)
        if isinstance(step, dict): step.pop("promo", None)
        try: bot.edit_message_reply_markup(chat_id=uid, message_id=call.message.message_id, reply_markup=deposit_amt_kb(uid, None))
        except: pass
        return
    if val == "custom":
        waiting[uid] = {"step": "dep_custom", "promo": _get_dep_promo(uid)}
        bot.send_message(uid, "✏️ <b>ផ្ញើចំនួន $ ដែលចង់ deposit:</b>", parse_mode="HTML", reply_markup=cancel_kb()); return

    amount = float(val)
    promo_code = _get_dep_promo(uid)
    waiting.pop(uid, None)
    _process_deposit(uid, uid_str, amount, promo_code)

def _get_dep_promo(uid):
    step = waiting.get(uid)
    return step.get("promo") if isinstance(step, dict) else None

def _process_deposit(uid, uid_str, amount, promo_code):
    lang = get_lang(uid)
    bonus, promo_applied = 0.0, None
    if promo_code:
        p = promos.get(promo_code.upper())
        if p and (p.get("uses", 0) == 0 or p.get("used", 0) < p.get("uses", 0)):
            if str(uid) not in p.get("user_used", {}):
                bonus = round(amount * float(p["discount"]) / 100, 2) if p.get("pct") else round(float(p["discount"]), 2)
                promo_applied = promo_code.upper()
    _send_deposit_qr(uid, amount, label=f"💸 <b>{'ដាក់លុយ' if lang=='kh' else 'Top Up'}</b>", bonus=bonus, promo_code_name=promo_applied)

# ═══════════════════════════════════════════════════════════
#  MAIN MESSAGE HANDLER
# ═══════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: True)
def handle(message):
    uid     = message.chat.id
    uid_str = str(uid)
    text    = message.text.strip() if message.text else ""
    step    = waiting.get(uid)

    _track_user(message)
    if is_banned(uid) and uid != ADMIN_ID: bot.send_message(uid, t(uid, "banned")); return

    if text in ("✕ Cancel", "❌ Cancel", "❌ បោះបង់"):
        waiting.pop(uid, None)
        kb = admin_kb() if uid == ADMIN_ID else main_kb(uid)
        bot.send_message(uid, t(uid, "cancel_ok"), reply_markup=kb); return

    # ── Admin Panel Commands ──
    if uid == ADMIN_ID:
        if isinstance(step, dict) and step.get("step") == "add_balance_amt":
            target = step["target"]
            try:
                amt = float(text.replace("$",""))
                add_bal(int(target), amt); waiting.pop(uid, None)
                bot.send_message(uid, f"✅ <b>បន្ថែម Balance</b> ទៅ <code>{target}</code> +${amt:.2f}", parse_mode="HTML", reply_markup=admin_kb())
            except: bot.send_message(uid, "❌ Amount ខុស!")
            return

        if isinstance(step, dict) and step.get("step") == "deduct_balance_amt":
            target = step["target"]
            try:
                amt = float(text.replace("$",""))
                ded_bal(int(target), amt); waiting.pop(uid, None)
                bot.send_message(uid, f"✅ <b>កាត់ Balance</b> ពី <code>{target}</code> -${amt:.2f}", parse_mode="HTML", reply_markup=admin_kb())
            except: bot.send_message(uid, "❌ Amount ខុស!")
            return

        if step == "promo_add_code":
            parts = text.strip().split()
            if len(parts) >= 4:
                code, discount, pct, uses = parts[0].upper(), float(parts[1]), (parts[2].lower() == "pct"), int(parts[3])
                promos[code] = {"discount": discount, "pct": pct, "uses": uses, "used": 0}
                _save(PROMO_FILE, promos); waiting.pop(uid, None)
                bot.send_message(uid, f"✅ <b>Promo Code Created: {code}</b>", parse_mode="HTML", reply_markup=admin_kb())
            else: bot.send_message(uid, "❌ Format ខុស!")
            return

        if step == "broadcast_msg": _do_broadcast(uid, message); return

        if text == "🎛️ កំណត់អត្រាឈ្នះ":
            bot.send_message(uid, f"🎛️ <b>កំណត់អត្រាឈ្នះ (RTP Control)</b>\n🎯 អត្រាឈ្នះបច្ចុប្បន្ន: <b>{get_win_rate()}%</b>", parse_mode="HTML", reply_markup=win_rate_kb()); return

        if text == "💰 កាបូបលុយ":
            lines = ["<b>💰 កាបូបលុយអ្នកប្រើ</b>\n━━━━━━━━━━━━━━━━━━"]
            for u_id, u_info in sorted(users_db.items(), key=lambda x: x[1].get("last",0), reverse=True)[:30]:
                lines.append(f"👤 <b>{u_info.get('name','?')}</b> <code>{u_id}</code> — <b>${bal(u_id):.2f}</b>")
            bot.send_message(uid, "\n".join(lines)[:4000], parse_mode="HTML", reply_markup=admin_kb()); return

        if text == "👥 អ្នកប្រើប្រាស់":
            users_sorted = sorted(users_db.items(), key=lambda x: x[1].get("last",0), reverse=True)
            if not users_sorted: bot.send_message(uid, "❌ គ្មានអ្នកប្រើប្រាស់ទេ!", reply_markup=admin_kb()); return
            msg_lines = [f"👥 <b>អ្នកប្រើប្រាស់សរុប ({len(users_sorted)} នាក់):</b>\n━━━━━━━━━━━━━━━━━━"]
            btns = []
            for u_id, u_info in users_sorted[:15]:
                b = bal(u_id)
                name = u_info.get("name","?") or "គ្មានឈ្មោះ"
                banned = u_info.get("banned", False)
                msg_lines.append(f"• 👤 <b>{name}</b> (<code>{u_id}</code>) | <b>${b:.2f}</b> " + ("🚫" if banned else "✅"))
                btns.append([
                    InlineKeyboardButton(f"👤 {name[:12]}", callback_data=f"useraction:addbal:{u_id}"),
                    InlineKeyboardButton("🔓 Unban" if banned else "🚫 Ban", callback_data=f"useraction:{'unban' if banned else 'ban'}:{u_id}")
                ])
            bot.send_message(uid, "\n".join(msg_lines), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns)); return

        if text == "💸 បន្ថែមប្រាក់":
            btns = [[InlineKeyboardButton(f"👤 {u_info.get('name','?')[:15]} (${bal(u_id):.2f})", callback_data=f"useraction:addbal:{u_id}")] for u_id, u_info in list(users_db.items())[:15]]
            bot.send_message(uid, "💸 <b>បន្ថែមប្រាក់ — ជ្រើសរើសអ្នកប្រើ៖</b>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns)); return

        if text == "💔 កាត់ប្រាក់":
            btns = [[InlineKeyboardButton(f"👤 {u_info.get('name','?')[:15]} (${bal(u_id):.2f})", callback_data=f"useraction:dedbal:{u_id}")] for u_id, u_info in list(users_db.items())[:15]]
            bot.send_message(uid, "💔 <b>កាត់ប្រាក់ — ជ្រើសរើសអ្នកប្រើ៖</b>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns)); return

        if text == "🎟️ លេខកូដPromo": _show_promos(uid); return
        if text == "📢 ផ្សព្វផ្សាយ":
            waiting[uid] = "broadcast_msg"
            bot.send_message(uid, "📢 <b>ផ្ញើ Message ដែលត្រូវផ្សព្វផ្សាយ:</b>", parse_mode="HTML", reply_markup=cancel_kb()); return

    # ── 🎮 ALL 6 GAMES LOGIC WITH RTP ──
    if text in ("🎰 ស្លុត", "🎰 ល្បែងស្លុត"):
        bet = get_user_bet(uid)
        if bal(uid) < bet: bot.send_message(uid, f"❌ <b>តុល្យភាពមិនគ្រប់គ្រាន់!</b> ត្រូវការ ${bet:.2f}", parse_mode="HTML"); return
        ded_bal(uid, bet)
        bot.send_dice(uid, emoji="🎰")
        time.sleep(2)
        if should_win():
            win_amt = round(bet * 5, 2); add_bal(uid, win_amt)
            bot.send_message(uid, f"🎊 <b>អ្នកឈ្នះរង្វាន់!</b>\n💰 ឈ្នះ: <b>+${win_amt:.2f}</b>\n💳 សមតុល្យ: <b>${bal(uid):.2f}</b>", parse_mode="HTML", reply_markup=main_kb(uid))
        else:
            bot.send_message(uid, f"😢 <b>មិនត្រូវទេ!</b>\n💸 កាត់: <b>-${bet:.2f}</b>\n💳 សមតុល្យ: <b>${bal(uid):.2f}</b>", parse_mode="HTML", reply_markup=main_kb(uid))
        return

    if text in ("🎲 ឡុកឡាក់ (តូច/ធំ)", "🎲 ឡុកឡាក់"):
        bot.send_message(uid, f"🎲 <b>ហ្គេមឡុកឡាក់ (តូច/ធំ)</b>\n🎯 ថ្លៃចាក់: <b>${get_user_bet(uid):.2f}</b>", parse_mode="HTML", reply_markup=dice_choice_kb()); return

    if text in ("🎯 បាញ់ស៊ីប",):
        bet = get_user_bet(uid)
        if bal(uid) < bet: bot.send_message(uid, f"❌ <b>តុល្យភាពមិនគ្រប់គ្រាន់!</b> ត្រូវការ ${bet:.2f}", parse_mode="HTML"); return
        ded_bal(uid, bet); bot.send_dice(uid, emoji="🎯"); time.sleep(2)
        if should_win():
            win_amt = round(bet * 3, 2); add_bal(uid, win_amt)
            bot.send_message(uid, f"🎯 <b>បាញ់ត្រូវស៊ីប!</b>\n💰 ឈ្នះ: <b>+${win_amt:.2f}</b>\n💳 សមតុល្យ: <b>${bal(uid):.2f}</b>", parse_mode="HTML", reply_markup=main_kb(uid))
        else: bot.send_message(uid, f"😢 <b>បាញ់ខុសស៊ីប!</b>\n💸 កាត់: <b>-${bet:.2f}</b>\n💳 សមតុល្យ: <b>${bal(uid):.2f}</b>", parse_mode="HTML", reply_markup=main_kb(uid))
        return

    if text in ("🏀 បោះបាល់",):
        bet = get_user_bet(uid)
        if bal(uid) < bet: bot.send_message(uid, f"❌ <b>តុល្យភាពមិនគ្រប់គ្រាន់!</b> ត្រូវការ ${bet:.2f}", parse_mode="HTML"); return
        ded_bal(uid, bet); bot.send_dice(uid, emoji="🏀"); time.sleep(2)
        if should_win():
            win_amt = round(bet * 2, 2); add_bal(uid, win_amt)
            bot.send_message(uid, f"🏀 <b>បោះបាល់ចូលកន្ត្រក!</b>\n💰 ឈ្នះ: <b>+${win_amt:.2f}</b>\n💳 សមតុល្យ: <b>${bal(uid):.2f}</b>", parse_mode="HTML", reply_markup=main_kb(uid))
        else: bot.send_message(uid, f"😢 <b>បោះបាល់ខុសកន្ត្រក!</b>\n💸 កាត់: <b>-${bet:.2f}</b>\n💳 សមតុល្យ: <b>${bal(uid):.2f}</b>", parse_mode="HTML", reply_markup=main_kb(uid))
        return

    if text in ("⚽ ទាត់បាល់",):
        bet = get_user_bet(uid)
        if bal(uid) < bet: bot.send_message(uid, f"❌ <b>តុល្យភាពមិនគ្រប់គ្រាន់!</b> ត្រូវការ ${bet:.2f}", parse_mode="HTML"); return
        ded_bal(uid, bet); bot.send_dice(uid, emoji="⚽"); time.sleep(2)
        if should_win():
            win_amt = round(bet * 1.8, 2); add_bal(uid, win_amt)
            bot.send_message(uid, f"⚽ <b>GOAL! ទាត់បាល់ចូលទីហើយ!</b>\n💰 ឈ្នះ: <b>+${win_amt:.2f}</b>\n💳 សមតុល្យ: <b>${bal(uid):.2f}</b>", parse_mode="HTML", reply_markup=main_kb(uid))
        else: bot.send_message(uid, f"😢 <b>ទាត់បាល់ខុសទី!</b>\n💸 កាត់: <b>-${bet:.2f}</b>\n💳 សមតុល្យ: <b>${bal(uid):.2f}</b>", parse_mode="HTML", reply_markup=main_kb(uid))
        return

    if text in ("🎳 ប៊ូលីង",):
        bet = get_user_bet(uid)
        if bal(uid) < bet: bot.send_message(uid, f"❌ <b>តុល្យភាពមិនគ្រប់គ្រាន់!</b> ត្រូវការ ${bet:.2f}", parse_mode="HTML"); return
        ded_bal(uid, bet); bot.send_dice(uid, emoji="🎳"); time.sleep(2)
        if should_win():
            win_amt = round(bet * 2.5, 2); add_bal(uid, win_amt)
            bot.send_message(uid, f"🎳 <b>STRIKE! រំលំដបប៊ូលីង!</b>\n💰 ឈ្នះ: <b>+${win_amt:.2f}</b>\n💳 សមតុល្យ: <b>${bal(uid):.2f}</b>", parse_mode="HTML", reply_markup=main_kb(uid))
        else: bot.send_message(uid, f"😢 <b>បោះប៊ូលីងខុស!</b>\n💸 កាត់: <b>-${bet:.2f}</b>\n💳 សមតុល្យ: <b>${bal(uid):.2f}</b>", parse_mode="HTML", reply_markup=main_kb(uid))
        return

    # ── User Menu Buttons ──
    if text in ("⚙️ កំណត់ថ្លៃចាក់",):
        bot.send_message(uid, f"⚙️ <b>កំណត់ថ្លៃចាក់ (បច្ចុប្បន្ន: ${get_user_bet(uid):.2f})</b>", parse_mode="HTML", reply_markup=bet_selection_kb(uid)); return

    if text in ("💰 ដាក់ប្រាក់", "💰 Top Up"):
        waiting.pop(uid, None)
        bot.send_message(uid, f"💸 <b>Top Up Wallet</b>\n💳 សាច់ប្រាក់: <b>${bal(uid):.2f}</b>\nជ្រើស ចំនួន ឬ ដាក់ Promo Code:", parse_mode="HTML", reply_markup=deposit_amt_kb(uid)); return

    if text in ("👜 កាបូបលុយ",):
        bot.send_message(uid, f"👜 <b>កាបូបលុយ</b>\n━━━━━━━━━━━━━━━━━━\n💳 សាច់ប្រាក់: <b>${bal(uid):.2f}</b>\n⚙️ ថ្លៃចាក់បច្ចុប្បន្ន: <b>${get_user_bet(uid):.2f}</b>", parse_mode="HTML", reply_markup=main_kb(uid)); return

    if text in ("💸 ដកប្រាក់",):
        waiting[uid] = {"step": "withdraw_enter_amount"}
        bot.send_message(uid, "✏️ <b>សូមផ្ញើចំនួន $ ដែលចង់ដក:</b>", parse_mode="HTML", reply_markup=cancel_kb()); return

    if text in ("💬 Support",):
        bot.send_message(uid, t(uid, "support_msg"), parse_mode="HTML", reply_markup=main_kb(uid)); return

    # ── Input Process ──
    if isinstance(step, dict) and step.get("step") == "custom_bet_amount":
        try:
            amt = float(text.replace("$",""))
            if MIN_BET <= amt <= MAX_BET:
                set_user_bet(uid, amt); waiting.pop(uid, None)
                bot.send_message(uid, f"✅ <b>បានកំណត់ថ្លៃចាក់: ${amt:.2f}</b>", parse_mode="HTML", reply_markup=main_kb(uid))
            else: bot.send_message(uid, f"❌ ចំនួនត្រូវតែចន្លោះ $0.10 ដល់ $50.00!")
        except: bot.send_message(uid, "❌ ចំនួនខុស!")
        return

    if isinstance(step, dict) and step.get("step") == "dep_enter_promo":
        code = text.strip().upper()
        _, _, err = apply_promo(uid, code, 1.0)
        if err: bot.send_message(uid, err + "\nព្យាយាមម្ដងទៀត:", reply_markup=cancel_kb()); return
        waiting[uid] = {"step": "dep_choose_amt", "promo": code}
        bot.send_message(uid, f"✅ Promo <b>{code}</b> បានភ្ជាប់!\nជ្រើសរើសចំនួន deposit:", parse_mode="HTML", reply_markup=deposit_amt_kb(uid, code)); return

    if isinstance(step, dict) and step.get("step") == "dep_custom":
        try:
            amount = float(text.replace("$",""))
            if amount >= 0.5:
                promo_code = step.get("promo"); waiting.pop(uid, None)
                _process_deposit(uid, uid_str, amount, promo_code)
            else: raise ValueError
        except: bot.send_message(uid, "❌ ចំនួនខុស! យ៉ាងហោច $0.50")
        return

    if isinstance(step, dict) and step.get("step") == "withdraw_enter_amount":
        try:
            amount = float(text.replace("$",""))
            if amount > 0:
                waiting[uid] = {"step": "withdraw_wait_photo", "amount": round(amount,2)}
                bot.send_message(uid, "📷 <b>សូមផ្ញើរូបភាព (screenshot/slip) សម្រាប់ការដកលុយ:</b>", parse_mode="HTML", reply_markup=cancel_kb())
            else: raise ValueError
        except: bot.send_message(uid, "❌ ចំនួនខុស!")
        return

    bot.send_message(uid, t(uid, "fallback"), reply_markup=main_kb(uid))

# ═══════════════════════════════════════════════════════════
#  BROADCAST & PHOTO / SLIP HANDLERS
# ═══════════════════════════════════════════════════════════
def _do_broadcast(admin_uid, message):
    waiting.pop(admin_uid, None)
    sent = failed = 0
    for u_id in list(users_db.keys()):
        try:
            if message.photo: bot.send_photo(int(u_id), message.photo[-1].file_id, caption=message.caption or "")
            elif message.video: bot.send_video(int(u_id), message.video.file_id, caption=message.caption or "")
            else: bot.send_message(int(u_id), message.text or "", parse_mode="HTML")
            sent += 1
        except: failed += 1
        time.sleep(0.05)
    bot.send_message(admin_uid, f"📢 <b>ផ្សព្វផ្សាយរួចរាល់!</b>\n✅ បានផ្ញើ: {sent} | ❌ បរាជ័យ: {failed}", parse_mode="HTML", reply_markup=admin_kb())

@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    uid = message.chat.id
    if uid == ADMIN_ID and waiting.get(uid) == "broadcast_msg":
        _do_broadcast(uid, message); return

    step = waiting.get(uid)
    if isinstance(step, dict) and step.get("step") == "withdraw_wait_photo":
        amt = step.get("amount", 0)
        u_info = users_db.get(str(uid), {})
        caption = f"💸 <b>Withdraw Request</b>\n👤 <code>{uid}</code> {u_info.get('name','')} @{u_info.get('username','')}\n💰 ចំនួនដក: <b>${amt:.2f}</b>"
        try: bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, parse_mode="HTML")
        except: pass
        bot.send_message(uid, "✅ បានផ្ញើសំណើដកប្រាក់ទៅ Admin ហើយ។", reply_markup=main_kb(uid))
        waiting.pop(uid, None)
    else:
        # ប្រសិនបើភ្ញៀវផ្ញើ Slip ដាក់ប្រាក់
        u_info = users_db.get(str(uid), {})
        caption = f"🧾 <b>Deposit Slip</b>\n👤 <code>{uid}</code> {u_info.get('name','')} @{u_info.get('username','')}"
        btns = [
            [InlineKeyboardButton("➕ បន្ថែម Balance ឱ្យភ្ញៀវ", callback_data=f"useraction:addbal:{uid}")]
        ]
        try:
            bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns))
            bot.send_message(uid, "✅ បានទទួលវិក្កយបត្រ (Slip)! Admin នឹងត្រួតពិនិត្យ និងបញ្ចូលទឹកប្រាក់ជូនភ្លាមៗ។")
        except: pass

# ═══════════════════════════════════════════════════════════
#  MAIN RUNNER
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    keep_alive()  # ចាប់ផ្តើម Web Server ការពារ Render Timeout
    logger.info("🚀 Kairozen Slot & Games Bot (RTP Version) កំពុងចាប់ផ្ដើម...")
    bot.infinity_polling(timeout=20, long_polling_timeout=15)
