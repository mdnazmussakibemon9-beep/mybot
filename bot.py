import os
import threading
import uuid
import logging
import requests
import re
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

# FFmpeg সচল করা
static_ffmpeg.add_paths()

# Render Web Service 24/7 সচল রাখার পোর্ট বাইন্ডার
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

def extract_yt_id(url):
    match = re.search(r"(?:v=|\/|youtu\.be\/)([0-9A-Za-z_-]{11})", url)
    return match.group(1) if match else None

def get_youtube_fallback_stream(yt_url, is_audio=False):
    video_id = extract_yt_id(yt_url)
    if not video_id:
        return None, None

    # ১. Piped / Invidious API
    invidious_apis = [
        f"https://pipedapi.kavin.rocks/streams/{video_id}",
        f"https://api.piped.privacydev.net/streams/{video_id}",
        f"https://vid.puffyan.us/api/v1/videos/{video_id}",
        f"https://inv.riverside.rocks/api/v1/videos/{video_id}"
    ]
    for endpoint in invidious_apis:
        try:
            r = requests.get(endpoint, timeout=8)
            if r.status_code == 200:
                data = r.json()
                title = data.get("title", "YouTube Media")
                if is_audio:
                    audio_streams = data.get("audioStreams", [])
                    if audio_streams:
                        # সেরা অডিও কোয়ালিটি নির্বাচন
                        best_aud = max(audio_streams, key=lambda x: x.get("bitrate", 0))
                        return best_aud.get("url"), title
                else:
                    video_streams = data.get("videoStreams", [])
                    if video_streams:
                        # 720p/360p সহ সাউন্ড সহ প্রোগ্রেসিভ স্ট্রিম অগ্রাধিকার
                        sound_vids = [v for v in video_streams if not v.get("videoOnly")]
                        if sound_vids:
                            return sound_vids[0].get("url"), title
                        return video_streams[0].get("url"), title
        except Exception:
            continue

    # ২. Cobalt API గేটওয়ে
    cobalt_instances = [
        "https://api.cobalt.tools/api/json",
        "https://cobalt.kwiatekm.pl/api/json",
        "https://co.wuk.sh/api/json"
    ]
    payload = {
        "url": yt_url,
        "isAudioOnly": is_audio,
        "aFormat": "mp3" if is_audio else "best",
        "vQuality": "720"
    }
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    for api in cobalt_instances:
        try:
            res = requests.post(api, json=payload, headers=headers, timeout=10)
            res_data = res.json()
            if res_data.get("url"):
                return res_data.get("url"), "YouTube Media"
        except Exception:
            continue

    return None, None

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
        await query.edit_message_text("❌ লিঙ্কের মেয়াদ শেষ। লিঙ্কটি আবার পাঠান।")
        return

    data = query.data
    req_type, quality = data.split("_")
    unique_id = str(uuid.uuid4())[:6]

    status_msg = await query.edit_message_text("⚡ ফাইল ডাউনলোড ও প্রসেসিং হচ্ছে, অপেক্ষা করুন...")
    output_dir = "temp_downloads"
    os.makedirs(output_dir, exist_ok=True)

    # ১. টিকটক ইঞ্জিন
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

    # ২. ইউটিউব মাল্টি-এপিআই ইঞ্জিন (ডাটা সেন্টার ব্লক বাইপাস)
    if "youtube.com" in url or "youtu.be" in url:
        direct_stream, yt_title = get_youtube_fallback_stream(url, is_audio=(req_type == "aud"))
        if direct_stream:
            try:
                ext = "mp4" if req_type == "vid" else "mp3"
                file_path = f"{output_dir}/yt_{unique_id}.{ext}"

                r = requests.get(direct_stream, stream=True, timeout=120)
                with open(file_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)

                await status_msg.edit_text("🚀 টেলিগ্রামে আপলোড হচ্ছে...")

                with open(file_path, "rb") as f:
                    if req_type == "vid":
                        await context.bot.send_video(
                            chat_id=user_id,
                            video=f,
                            supports_streaming=True,
                            caption=f"✅ {yt_title[:60]}"
                        )
                    else:
                        await context.bot.send_audio(
                            chat_id=user_id,
                            audio=f,
                            title=yt_title[:40],
                            performer="YouTube"
                        )

                await status_msg.delete()
                if os.path.exists(file_path):
                    os.remove(file_path)
                return
            except Exception:
                pass

    # ৩. ফেসবুক ও ইনস্টাগ্রাম (yt-dlp ইঞ্জিন)
    output_template = f"{output_dir}/media_{unique_id}.%(ext)s"
    ydl_opts = {
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'format': 'best' if req_type == "vid" else 'bestaudio/best',
    }
    if req_type == "aud":
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    file_path = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_title = info.get('title', 'Media')
            channel_name = info.get('uploader', 'Artist')
            file_path = ydl.prepare_filename(info)

            base_name = os.path.splitext(file_path)[0]
            ext = ".mp4" if req_type == "vid" else ".mp3"
            if os.path.exists(base_name + ext):
                file_path = base_name + ext

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
                await context.bot.send_audio(
                    chat_id=user_id,
                    audio=f,
                    title=video_title,
                    performer=channel_name
                )

        await status_msg.delete()
    except Exception as e:
        await context.bot.send_message(chat_id=user_id, text=f"ত্রুটি: {str(e)[:150]}")
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
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
