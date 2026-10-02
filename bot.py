import os
import threading
import uuid
import logging
import requests
import static_ffmpeg
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.request import HTTPXRequest
import yt_dlp
from PIL import Image

# FFmpeg সক্রিয় করা
static_ffmpeg.add_paths()

# Render Web Service Live রাখার ব্যাকগ্রাউন্ড পোর্ট
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Telegram Media Downloader Bot is Running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

BOT_TOKEN = "8826750975:AAEQB-Lhqq3FrFyOVL7mXWqtC9CdcH1HvOI"
user_urls = {}

def get_tiktok_direct_url(tiktok_url):
    try:
        api_url = f"https://tikwm.com/api/?url={tiktok_url}"
        res = requests.get(api_url, timeout=15).json()
        if res.get("code") == 0:
            data = res.get("data", {})
            return {
                "title": data.get("title", "TikTok Video"),
                "video_url": data.get("play"),
                "audio_url": data.get("music"),
                "cover": data.get("cover"),
                "author": data.get("author", {}).get("nickname", "TikTok User"),
                "duration": data.get("duration", 0)
            }
    except Exception:
        pass
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "⚡ সুপার ফাস্ট অল-ইন-ওয়ান ডাউনলোডার বট প্রস্তুত!\n\n"
        "যেকোনো প্ল্যাটফর্মের ভিডিও লিঙ্ক পাঠান (YouTube, TikTok, Facebook, Insta ইত্যাদি)।"
    )
    await update.message.reply_text(welcome_text)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user_id = update.effective_user.id
    user_urls[user_id] = url

    keyboard = [
        [
            InlineKeyboardButton("🎬 Best Video", callback_data="vid_best"),
            InlineKeyboardButton("📱 Fast Video", callback_data="vid_fast")
        ],
        [
            InlineKeyboardButton("🎵 MP3 Audio (With Cover & Title)", callback_data="aud_best")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("কোন ফরম্যাটে ডাউনলোড করতে চান বেছে নিন:", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    url = user_urls.get(user_id)

    if not url:
        await query.edit_message_text("❌ লিঙ্কের মেয়াদ শেষ। দয়া করে লিঙ্কটি আবার পাঠান।")
        return

    data = query.data
    req_type, quality = data.split("_")
    unique_id = str(uuid.uuid4())[:6]

    status_msg = await query.edit_message_text("⚡ ফাইল ডাউনলোড ও প্রসেসিং হচ্ছে, অপেক্ষা করুন...")
    output_dir = "temp_downloads"
    os.makedirs(output_dir, exist_ok=True)

    # TikTok Direct API
    if "tiktok.com" in url:
        tk_data = get_tiktok_direct_url(url)
        if tk_data:
            try:
                target_url = tk_data["video_url"] if req_type == "vid" else tk_data["audio_url"]
                ext = "mp4" if req_type == "vid" else "mp3"
                file_path = f"{output_dir}/tk_{unique_id}.{ext}"

                r = requests.get(target_url, stream=True, timeout=60)
                with open(file_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)

                thumb_path = None
                if tk_data.get("cover"):
                    thumb_path = f"{output_dir}/thumb_{unique_id}.jpg"
                    tr = requests.get(tk_data["cover"], timeout=15)
                    with open(thumb_path, "wb") as tf:
                        tf.write(tr.content)

                await status_msg.edit_text("🚀 টেলিগ্রামে আপলোড হচ্ছে...")

                with open(file_path, "rb") as f:
                    if req_type == "vid":
                        await context.bot.send_video(
                            chat_id=user_id,
                            video=f,
                            supports_streaming=True,
                            caption=f"✅ {tk_data['title'][:60]}"
                        )
                    else:
                        if thumb_path and os.path.exists(thumb_path):
                            with open(thumb_path, "rb") as t:
                                await context.bot.send_audio(
                                    chat_id=user_id,
                                    audio=f,
                                    thumbnail=t,
                                    title=tk_data["title"][:40],
                                    performer=tk_data["author"],
                                    duration=tk_data["duration"]
                                )
                        else:
                            await context.bot.send_audio(
                                chat_id=user_id,
                                audio=f,
                                title=tk_data["title"][:40],
                                performer=tk_data["author"]
                            )

                await status_msg.delete()
                if os.path.exists(file_path):
                    os.remove(file_path)
                if thumb_path and os.path.exists(thumb_path):
                    os.remove(thumb_path)
                return
            except Exception as e:
                await context.bot.send_message(chat_id=user_id, text=f"টিকটক ডাউনলোডে ত্রুটি: {str(e)[:100]}")
                return

    output_template = f"{output_dir}/media_{unique_id}.%(ext)s"

    # খাঁটি Android Client যাতে কোনো Reload / Cookies এরর না আসে
    common_opts = {
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android'],
                'player_skip': ['webpage', 'configs']
            }
        },
    }

    if req_type == "vid":
        ydl_opts = {
            **common_opts,
            'format': 'best[ext=mp4]/best',
        }
    else:
        ydl_opts = {
            **common_opts,
            'format': 'bestaudio/best',
            'writethumbnail': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

    file_path = None
    thumb_jpg = None

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_title = info.get('title', 'Media')
            channel_name = info.get('uploader', 'Unknown Artist')
            duration = info.get('duration', 0)
            file_path = ydl.prepare_filename(info)

            if req_type == "vid":
                base_name = os.path.splitext(file_path)[0]
                if os.path.exists(base_name + ".mp4"):
                    file_path = base_name + ".mp4"
            else:
                base_name = os.path.splitext(file_path)[0]
                if os.path.exists(base_name + ".mp3"):
                    file_path = base_name + ".mp3"

        if req_type == "aud":
            base_path = os.path.splitext(file_path)[0]
            for ext in ['.webp', '.jpg', '.jpeg', '.png']:
                potential_thumb = base_path + ext
                if os.path.exists(potential_thumb):
                    try:
                        im = Image.open(potential_thumb).convert("RGB")
                        thumb_jpg = base_path + "_thumb.jpg"
                        im.save(thumb_jpg, "JPEG")
                        os.remove(potential_thumb)
                    except Exception:
                        pass
                    break

        await status_msg.edit_text("🚀 টেলিগ্রামে আপলোড হচ্ছে...")

        with open(file_path, 'rb') as f:
            if req_type == "vid":
                await context.bot.send_video(
                    chat_id=user_id,
                    video=f,
                    supports_streaming=True,
                    caption=f"✅ {video_title}"
                )
            else:
                if thumb_jpg and os.path.exists(thumb_jpg):
                    with open(thumb_jpg, 'rb') as t:
                        await context.bot.send_audio(
                            chat_id=user_id,
                            audio=f,
                            thumbnail=t,
                            title=video_title,
                            performer=channel_name,
                            duration=duration
                        )
                else:
                    await context.bot.send_audio(
                        chat_id=user_id,
                        audio=f,
                        title=video_title,
                        performer=channel_name,
                        duration=duration
                    )

        await status_msg.delete()

    except Exception as e:
        await context.bot.send_message(chat_id=user_id, text=f"Error: {str(e)[:150]}")

    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        if thumb_jpg and os.path.exists(thumb_jpg):
            try:
                os.remove(thumb_jpg)
            except Exception:
                pass

def main():
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()

    custom_request = HTTPXRequest(
        connect_timeout=60.0,
        read_timeout=300.0,
        write_timeout=300.0
    )
    app = ApplicationBuilder().token(BOT_TOKEN).request(custom_request).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
