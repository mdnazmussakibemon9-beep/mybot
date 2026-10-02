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

# FFmpeg যুক্ত করা
static_ffmpeg.add_paths()

# Render Web Service 24/7 লাইভ রাখার ব্যাকগ্রাউন্ড পোর্ট
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Social Downloader Bot is Running 24/7!"

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
                "video_hd": data.get("hdplay") or data.get("play"),
                "video_sd": data.get("play"),
                "audio_url": data.get("music"),
                "cover_hd": data.get("origin_cover") or data.get("cover"),
                "cover_sd": data.get("cover"),
                "author": data.get("author", {}).get("nickname", "TikTok Creator"),
                "duration": data.get("duration", 0)
            }
    except Exception:
        pass
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "⚡ **আল্টিমেট অল-ইন-ওয়ান ডাউনলোডার বট!**\n\n"
        "Facebook, Instagram, TikTok ইত্যাদির যেকোনো ভিডিও লিঙ্ক পাঠান।\n\n"
        "🎥 **ভিডিও:** 1080p, 720p, 480p, 360p, 240p, 144p\n"
        "🎵 **অডিও:** 320k, 192k, 128k (MP3 with Cover)\n"
        "🖼️ **থাম্বনেইল:** HD ও Standard কোয়ালিটি"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user_id = update.effective_user.id

    if "youtube.com" in url or "youtu.be" in url:
        await update.message.reply_text(
            "⚠️ দুঃখিত! ইউটিউব ডাউনলোডের জন্য আলাদা বট নির্ধারিত রয়েছে।\n"
            "এখানে শুধুমাত্র TikTok, Facebook, Instagram ইত্যাদির লিঙ্ক পাঠান।"
        )
        return

    user_urls[user_id] = url

    # সব কোয়ালিটি ও কাস্টম রেজোলিউশনের সম্পূর্ণ বাটন প্যানেল
    keyboard = [
        # কুইক ভিডিও অপশন
        [
            InlineKeyboardButton("🌟 Highest (Max)", callback_data="vid_highest"),
            InlineKeyboardButton("🎬 Normal (Balanced)", callback_data="vid_normal"),
            InlineKeyboardButton("🚀 Fast (Low Size)", callback_data="vid_fast")
        ],
        # কাস্টম রেজোলিউশন অপশন
        [
            InlineKeyboardButton("📺 1080p", callback_data="vid_1080"),
            InlineKeyboardButton("📺 720p", callback_data="vid_720"),
            InlineKeyboardButton("📱 480p", callback_data="vid_480")
        ],
        [
            InlineKeyboardButton("📱 360p", callback_data="vid_360"),
            InlineKeyboardButton("⚡ 240p", callback_data="vid_240"),
            InlineKeyboardButton("⚡ 144p", callback_data="vid_144")
        ],
        # অডিও অপশন
        [
            InlineKeyboardButton("🎵 Audio High (320k)", callback_data="aud_320"),
            InlineKeyboardButton("🎶 Mid (192k)", callback_data="aud_192"),
            InlineKeyboardButton("📻 Low (128k)", callback_data="aud_128")
        ],
        # থাম্বনেইল অপশন
        [
            InlineKeyboardButton("🖼️ Thumbnail HD", callback_data="thumb_hd"),
            InlineKeyboardButton("🖼️ Thumbnail Standard", callback_data="thumb_sd")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📥 আপনার পছন্দের কোয়ালিটি বা রেজোলিউশন বেছে নিন:", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    url = user_urls.get(user_id)

    if not url:
        await query.edit_message_text("❌ লিঙ্কের মেয়াদ শেষ হয়ে গেছে। লিঙ্কটি পুনরায় পাঠান।")
        return

    data = query.data
    req_type, quality = data.split("_")
    unique_id = str(uuid.uuid4())[:6]

    quality_display = {
        "highest": "🌟 Highest Quality",
        "normal": "🎬 Normal Quality",
        "fast": "🚀 Fast Download",
        "1080": "📺 1080p Full HD",
        "720": "📺 720p HD",
        "480": "📱 480p",
        "360": "📱 360p",
        "240": "⚡ 240p Low",
        "144": "⚡ 144p Ultra Low",
        "320": "🎵 Audio High (320 kbps)",
        "192": "🎶 Audio Medium (192 kbps)",
        "128": "📻 Audio Low (128 kbps)",
        "hd": "🖼️ High Definition Thumbnail",
        "sd": "🖼️ Standard Thumbnail"
    }.get(quality, quality)

    status_msg = await query.edit_message_text(f"⚡ {quality_display} প্রসেসিং হচ্ছে, অপেক্ষা করুন...")
    output_dir = "temp_downloads"
    os.makedirs(output_dir, exist_ok=True)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    # ১. টিকটক ইঞ্জিন
    if "tiktok.com" in url:
        tk_data = get_tiktok_direct_url(url)
        if tk_data:
            file_path = None
            thumb_path = None
            try:
                # থাম্বনেইল ডাউনলোড
                if req_type == "thumb":
                    target_url = tk_data["cover_hd"] if quality == "hd" else tk_data["cover_sd"]
                    file_path = f"{output_dir}/tk_thumb_{unique_id}.jpg"
                    r = requests.get(target_url, headers=headers, timeout=20)
                    with open(file_path, "wb") as f:
                        f.write(r.content)
                    
                    await status_msg.edit_text("🚀 থাম্বনেইল পাঠানো হচ্ছে...")
                    with open(file_path, "rb") as f:
                        await context.bot.send_photo(
                            chat_id=user_id,
                            photo=f,
                            caption=f"✅ {tk_data['title'][:60]}\n🎯 {quality_display}"
                        )
                    await status_msg.delete()
                    return

                # ভিডিও বা অডিও
                if req_type == "vid":
                    # হাই কোয়ালিটি অথবা লো কোয়ালিটি নির্বাচন
                    target_url = tk_data["video_hd"] if quality in ["highest", "1080", "720"] else tk_data["video_sd"]
                    ext = "mp4"
                else:
                    target_url = tk_data["audio_url"]
                    ext = "mp3"

                file_path = f"{output_dir}/tk_{unique_id}.{ext}"

                with requests.get(target_url, stream=True, headers=headers, timeout=60) as r:
                    r.raise_for_status()
                    with open(file_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024*1024):
                            if chunk:
                                f.write(chunk)

                if tk_data.get("cover_sd"):
                    thumb_path = f"{output_dir}/thumb_{unique_id}.jpg"
                    tr = requests.get(tk_data["cover_sd"], headers=headers, timeout=15)
                    with open(thumb_path, "wb") as tf:
                        tf.write(tr.content)

                await status_msg.edit_text("🚀 টেলিগ্রামে আপলোড হচ্ছে...")

                with open(file_path, "rb") as f:
                    if req_type == "vid":
                        await context.bot.send_video(
                            chat_id=user_id,
                            video=f,
                            supports_streaming=True,
                            caption=f"✅ {tk_data['title'][:60]}\n🎯 {quality_display}"
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
                return
            except Exception as e:
                await context.bot.send_message(chat_id=user_id, text=f"টিকটক ত্রুটি: {str(e)[:100]}")
                return
            finally:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                if thumb_path and os.path.exists(thumb_path):
                    os.remove(thumb_path)

    # ২. Facebook, Instagram এবং অন্যান্য সাইটের ইঞ্জিন
    output_template = f"{output_dir}/media_{unique_id}.%(ext)s"

    # থাম্বনেইল ডাউনলোড হ্যান্ডলার
    if req_type == "thumb":
        ydl_opts = {
            'skip_download': True,
            'writethumbnail': True,
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
        }
        file_path = None
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_title = info.get('title', 'Media')
                thumb_url = info.get('thumbnail')

                if quality == "hd" and info.get('thumbnails'):
                    thumb_url = info['thumbnails'][-1].get('url', thumb_url)

                if thumb_url:
                    file_path = f"{output_dir}/thumb_{unique_id}.jpg"
                    r = requests.get(thumb_url, headers=headers, timeout=20)
                    with open(file_path, "wb") as f:
                        f.write(r.content)

            if file_path and os.path.exists(file_path):
                await status_msg.edit_text("🚀 থাম্বনেইল পাঠানো হচ্ছে...")
                with open(file_path, "rb") as f:
                    await context.bot.send_photo(
                        chat_id=user_id,
                        photo=f,
                        caption=f"✅ {video_title[:60]}\n🎯 {quality_display}"
                    )
                await status_msg.delete()
            else:
                await status_msg.edit_text("❌ থাম্বনেইল পাওয়া যায়নি।")
        except Exception as e:
            await context.bot.send_message(chat_id=user_id, text=f"থাম্বনেইল ত্রুটি: {str(e)[:150]}")
        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        return

    # ভিডিও ও অডিও কনফিগারেশন
    if req_type == "vid":
        # কাস্টম রেজোলিউশন ফিল্টার
        if quality == "highest":
            format_opt = "bestvideo+bestaudio/best"
        elif quality == "normal":
            format_opt = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
        elif quality == "fast":
            format_opt = "worstvideo[height<=480]+worstaudio/worst"
        elif quality.isdigit():
            h = int(quality)
            format_opt = f"bestvideo[height<={h}]+bestaudio/best[height<={h}]/best"
        else:
            format_opt = "bestvideo+bestaudio/best"

        ydl_opts = {
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'format': format_opt,
            'merge_output_format': 'mp4',
        }
    else:
        # নির্দিষ্ট অডিও বিটরেট
        bitrate = quality if quality in ["320", "192", "128"] else "192"
        ydl_opts = {
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'format': 'bestaudio/best',
            'writethumbnail': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': bitrate,
            }],
        }

    file_path = None
    thumb_jpg = None

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_title = info.get('title', 'Media')
            channel_name = info.get('uploader', 'Artist')
            duration = info.get('duration', 0)
            file_path = ydl.prepare_filename(info)

            base_name = os.path.splitext(file_path)[0]
            if req_type == "vid":
                if os.path.exists(base_name + ".mp4"):
                    file_path = base_name + ".mp4"
            else:
                if os.path.exists(base_name + ".mp3"):
                    file_path = base_name + ".mp3"

        # অডিও থাম্বনেইল সংরক্ষণ
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
                    caption=f"✅ {video_title[:60]}\n🎯 কোয়ালিটি: {quality_display}"
                )
            else:
                if thumb_jpg and os.path.exists(thumb_jpg):
                    with open(thumb_jpg, 'rb') as t:
                        await context.bot.send_audio(
                            chat_id=user_id,
                            audio=f,
                            thumbnail=t,
                            title=video_title[:40],
                            performer=channel_name[:30],
                            duration=duration
                        )
                else:
                    await context.bot.send_audio(
                        chat_id=user_id,
                        audio=f,
                        title=video_title[:40],
                        performer=channel_name[:30],
                        duration=duration
                    )

        await status_msg.delete()

    except Exception as e:
        await context.bot.send_message(chat_id=user_id, text=f"ডাউনলোডে ত্রুটি: {str(e)[:150]}")

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

    print("Custom Resolutions Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
