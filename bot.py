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
RAPIDAPI_KEY = "56530a173fmsh8e9c96b676755abp148422jsnf768ba7c0228"
RAPIDAPI_HOST = "youtube-media-downloader.p.rapidapi.com"

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

def get_youtube_rapidapi(yt_url, is_audio=False, fast_video=False):
    vid_id = extract_yt_id(yt_url)
    if not vid_id:
        return None, None, None, None

    url = "https://youtube-media-downloader.p.rapidapi.com/v2/video/details"
    querystring = {"videoId": vid_id}
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }

    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=20)
        data = response.json()
        title = data.get("title", "YouTube Media")
        channel = data.get("channelTitle", "YouTube")
        duration = data.get("lengthSeconds", 0)
        thumbnails = data.get("thumbnails", [])
        thumb_url = thumbnails[-1].get("url") if thumbnails else None

        if is_audio:
            audios = data.get("audios", {}).get("items", [])
            if audios:
                return audios[0].get("url"), title, channel, thumb_url
        else:
            videos = data.get("videos", {}).get("items", [])
            if videos:
                with_audio = [v for v in videos if v.get("hasAudio")]
                target_list = with_audio if with_audio else videos
                if fast_video and len(target_list) > 1:
                    # ফাস্ট ভিডিওর জন্য তুলনামূলক ছোট সাইজ
                    return target_list[-1].get("url"), title, channel, thumb_url
                return target_list[0].get("url"), title, channel, thumb_url
    except Exception:
        pass
    return None, None, None, None

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

    status_msg = await query.edit_message_text("⚡ ফাইল প্রস্তুত করা হচ্ছে, অপেক্ষা করুন...")
    output_dir = "temp_downloads"
    os.makedirs(output_dir, exist_ok=True)

    browser_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    # ১. টিকটক
    if "tiktok.com" in url:
        tk_data = get_tiktok_direct_url(url)
        if tk_data:
            try:
                target_url = tk_data["video_url"] if req_type == "vid" else tk_data["audio_url"]
                ext = "mp4" if req_type == "vid" else "mp3"
                file_path = f"{output_dir}/tk_{unique_id}.{ext}"

                with requests.get(target_url, stream=True, headers=browser_headers, timeout=60) as r:
                    r.raise_for_status()
                    with open(file_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024*1024):
                            if chunk:
                                f.write(chunk)

                thumb_path = None
                if tk_data.get("cover"):
                    thumb_path = f"{output_dir}/thumb_{unique_id}.jpg"
                    tr = requests.get(tk_data["cover"], headers=browser_headers, timeout=15)
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
                await context.bot.send_message(chat_id=user_id, text=f"টিকটক ত্রুটি: {str(e)[:100]}")
                return

    # ২. ইউটিউব ইঞ্জিন
    if "youtube.com" in url or "youtu.be" in url:
        is_audio = (req_type == "aud")
        fast_video = (quality == "fast")
        stream_url, yt_title, yt_artist, yt_thumb = get_youtube_rapidapi(url, is_audio=is_audio, fast_video=fast_video)
        
        if stream_url:
            label = "🎵 অডিও" if is_audio else ("📱 ফাস্ট ভিডিও" if fast_video else "🎬 বেস্ট ভিডিও")
            download_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"⬇️ সরাসরি ডাউনলোড করুন ({label})", url=stream_url)]
            ])
            caption = f"✅ **{yt_title}**\n\nচ্যানেল: {yt_artist}\n\nRender ক্লাউড আইপি ব্লকের কারণে নিচে সরাসরি ডাউনলোড বাটন দেওয়া হলো:"
            await status_msg.edit_text(caption, reply_markup=download_markup, parse_mode="Markdown")
            return
        else:
            await status_msg.edit_text("❌ ইউটিউব লিঙ্ক প্রসেস করা যায়নি। দয়া করে অন্য ভিডিও লিঙ্ক দিয়ে চেষ্টা করুন।")
            return

    # ৩. অন্যান্য সাইট (Facebook, Instagram)
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
