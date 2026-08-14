import os
import sys
import asyncio
import threading
import subprocess
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

# បន្ថែម static_ffmpeg ដើម្បីកុំឱ្យខ្វះ ffmpeg លើ Render
import static_ffmpeg
static_ffmpeg.add_paths()

# ----------------- Render Web Server (Port Binding) -----------------
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running 24/7!")

def run_web():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_web, daemon=True).start()

# ----------------- Windows event loop fix -----------------
if sys.platform == 'win32':
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from google import genai
import edge_tts

# ----------------- Configuration -----------------
API_ID = 24900598
API_HASH = "9dc6d9d36a16cccbdadd9aaa2cd3533a"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6LYTYANfXCmCKgalrzu-oGBq7quacDjkAsBsD6AepERMw")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8749297297:AAEvWT7qku12vRkcsbkX9oE117cCWWpPrCY")

client_gemini = genai.Client(api_key=GEMINI_API_KEY)

VOICE_OPTIONS = {
    "voice_male": "km-KH-PisethNeural",
    "voice_female": "km-KH-SreymomNeural"
}

user_sessions = {}
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
app = Client("free_fast_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ----------------- Fast Functions -----------------
def extract_fast_audio(video_path, audio_path):
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "libmp3lame", "-b:a", "32k", "-ar", "16000", "-ac", "1",
        audio_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def translate_fast_with_gemini(audio_path):
    try:
        audio_file = client_gemini.files.upload(file=audio_path)
        prompt = "Translate all speech in this audio to spoken Khmer directly. Output only the Khmer translation text without notes."
        
        response = client_gemini.models.generate_content(
            model="gemini-2.5-flash",
            contents=[audio_file, prompt]
        )
        
        try:
            client_gemini.files.delete(name=audio_file.name)
        except Exception:
            pass
            
        return response.text.strip() if response.text else ""
    except Exception as e:
        print(f"Error AI: {e}")
        return ""

async def generate_khmer_voice(text, voice_code, output_audio):
    communicate = edge_tts.Communicate(text, voice_code)
    await communicate.save(output_audio)

def merge_video_fast(video_path, khmer_audio_path, output_video):
    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", khmer_audio_path,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        output_video
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

# ----------------- Handlers -----------------
@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text("👋 សួស្តី! ខ្ញុំជា Bot បកប្រែវីដេអូជាភាសាខ្មែរ។ សូមផ្ញើវីដេអូមក!")

@app.on_message(filters.video | filters.document)
async def handle_video(client, message):
    user_id = message.from_user.id
    status_msg = await message.reply_text("⚡ [1/4] កំពុងទាញយកវីដេអូ...")

    input_video = f"in_{user_id}.mp4"
    audio_orig = f"orig_{user_id}.mp3"

    try:
        await message.download(file_name=input_video)
        
        await status_msg.edit_text("⚡ [2/4] កំពុងស្ដាប់ និងបកប្រែជាភាសាខ្មែរ...")
        extract_fast_audio(input_video, audio_orig)
        khmer_text = translate_fast_with_gemini(audio_orig)

        if not khmer_text:
            await status_msg.edit_text("⚠️ មិនអាចស្ដាប់ឮ ឬបកប្រែសំឡេងក្នុងវីដេអូនេះទេ។")
            if os.path.exists(input_video): os.remove(input_video)
            return

        user_sessions[user_id] = {
            "khmer_text": khmer_text,
            "video_path": input_video
        }

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("👨 សំឡេងប្រុស (ពិសិដ្ឋ)", callback_data="voice_male"),
                InlineKeyboardButton("👩 សំឡេងស្រី (ស្រីមុំ)", callback_data="voice_female"),
            ]
        ])

        preview = khmer_text[:200] + "..." if len(khmer_text) > 200 else khmer_text
        await status_msg.edit_text(
            f"📝 **អត្ថបទបកប្រែ៖**\n{preview}\n\n👇 **សូមជ្រើសរើសសំឡេង៖**",
            reply_markup=buttons,
            parse_mode=ParseMode.DEFAULT
        )

    except Exception as e:
        print(f"Error handling video: {e}")
        await status_msg.edit_text("❌ មានបញ្ហាក្នុងការដំណើរការ។")
        if os.path.exists(input_video):
            os.remove(input_video)
    finally:
        if os.path.exists(audio_orig):
            os.remove(audio_orig)

@app.on_callback_query()
async def on_voice_select(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    session = user_sessions.get(user_id)

    if not session or not os.path.exists(session["video_path"]):
        await callback.answer("⚠️ វីដេអូផុតកំណត់ សូមផ្ញើម្តងទៀត!", show_alert=True)
        return

    await callback.answer()
    voice_code = VOICE_OPTIONS.get(callback.data)

    await callback.edit_message_text("⚡ [3/4] កំពុងបង្កើតសំឡេង និង Render វីដេអូ...")

    input_video = session["video_path"]
    khmer_text = session["khmer_text"]
    audio_khmer = f"kh_{user_id}.mp3"
    output_video = f"out_{user_id}.mp4"

    try:
        await generate_khmer_voice(khmer_text, voice_code, audio_khmer)
        merge_video_fast(input_video, audio_khmer, output_video)

        await callback.edit_message_text("⚡ [4/4] កំពុងផ្ញើវីដេអូត្រឡប់ទៅវិញ...")
        
        await client.send_video(
            chat_id=callback.message.chat.id,
            video=output_video,
            caption="🇰🇭 **វីដេអូបកប្រែរួចរាល់!**",
            supports_streaming=True
        )
        await callback.message.delete()

    except Exception as e:
        print(f"Error rendering: {e}")
        await callback.edit_message_text("❌ បរាជ័យក្នុងការ Render វីដេអូ។")
    finally:
        for f in [input_video, audio_khmer, output_video]:
            if os.path.exists(f):
                os.remove(f)
        user_sessions.pop(user_id, None)

if __name__ == "__main__":
    print("🚀 Bot កំពុងដំណើរការ...")
    app.run()
