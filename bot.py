import os
import threading
import uuid
import logging
import subprocess
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

# FFmpeg সচল করা
static_ffmpeg.add_paths()

# Render Web Service 24/7 লাইভ রাখার ওয়েব সার্ভার
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Ultra Social Media Downloader Bot is Running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

BOT_TOKEN = "8826750975:AAEQB-Lhqq3FrFyOVL7mXWqtC9CdcH1HvOI"

# ডাটা স্টোরেজ
user_urls = {}
user_waiting_custom_time = {}
user_languages = {}

# বাংলা ও ইংরেজির পূর্ণাঙ্গ টেক্সট ও ব্যবহার নির্দেশিকা
TEXTS = {
    "bn": {
        "guide": (
            "🌟 **সোশ্যাল মিডিয়া ডাউনলোডার বটে স্বাগতম!** 🌟\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 **কোন বাটন কী কাজ করে জেনে নিন:**\n\n"
            "🎥 **ভিডিও ডাউনলোড:**\n"
            "• `Highest (1080p)`: সর্বোচ্চ স্পষ্ট কোয়ালিটি\n"
            "• `Normal (720p)`: স্ট্যান্ডার্ড রেজোলিউশন\n"
            "• `Fast (Low Size)`: খুব দ্রুত ও কম মেগাবাইটে ডাউনলোড\n"
            "• `1080p, 720p, 480p, 360p, 240p, 144p`: নির্দিষ্ট রেজোলিউশন\n"
            "• `📁 Document`: কোনো কম্প্রেশন ছাড়া আসল ফাইল\n\n"
            "🎵 **অডিও ও টুলস:**\n"
            "• `320k, 192k, 128k`: সেরা সাউন্ড কোয়ালিটির MP3 গান\n"
            "• `🎙️ Voice Note`: সরাসরি টেলিগ্রাম ভয়েস মেসেজ\n"
            "• `🎞️ Animated GIF`: ছোট ভিডিওকে GIF অ্যানিমেশন করা\n\n"
            "🖼️ **থাম্বনেইল ও ফ্রেম:**\n"
            "• `Thumb HD / Std`: ভিডিওর কভার ছবি ডাউনলোড\n"
            "• `⏱️ Mid Frame`: ভিডিওর ঠিক মাঝখানের দৃশ্য ক্যাপচার\n"
            "• `⏳ Custom Frame`: যেকোনো সেকেন্ডের ফ্রেম ছবি আকারে নেওয়া\n\n"
            "💡 **ব্যবহারের নিয়ম:** যেকোনো পাবলিক লিঙ্ক (TikTok, Facebook, Insta, X, Reddit, Pinterest) সরাসরি চ্যাটে পাঠিয়ে দিন!"
        ),
        "help_text": (
            "📖 **জরুরি নির্দেশনা ও সমাধান:**\n\n"
            "1️⃣ **ভাষা পরিবর্তন:** /lang কমান্ড দিন অথবা 'ভাষা পরিবর্তন' লিখুন।\n"
            "2️⃣ **৫০ MB লিমিট:** টেলিগ্রাম বট ৫০ MB-র বড় ফাইল পাঠাতে পারে না। বড় ভিডিও হলে 480p বা Fast মোড বেছে নিন।\n"
            "3️⃣ **কাস্টম ফ্রেম:** 'Custom Frame' বাটনে চাপ দিয়ে সেকেন্ড লিখে পাঠান (যেমন: 15 বা 01:20)।\n"
            "4️⃣ **সমস্যা হলে:** ভিডিওটি পাবলিক কি না তা যাচাই করুন।"
        ),
        "help_lang_resp": "🌐 ভাষা পরিবর্তন করতে নিচের বাটনে চাপ দিন অথবা /lang লিখুন:",
        "help_error_resp": (
            "🛠️ **ডাউনলোডে সমস্যা হচ্ছে?**\n\n"
            "• নিশ্চিত করুন ভিডিও লিঙ্কটি পাবলিক (প্রাইভেট অ্যাকাউন্ট সাপোর্ট করে না)।\n"
            "• ফাইল খুব বড় হলে কম রেজোলিউশন (720p/480p) নির্বাচন করুন।\n"
            "• লিঙ্কটি পুনরায় পাঠিয়ে চেষ্টা করুন।"
        ),
        "help_size_resp": "ℹ️ টেলিগ্রাম বটে সর্বোচ্চ ৫০ MB পর্যন্ত ফাইল পাঠানো যায়। বড় ভিডিও হলে 480p বা 360p সিলেক্ট করলে সহজে ডাউনলোড হবে।",
        "choose_option": "📥 আপনার পছন্দের কোয়ালিটি বা ফরম্যাট বেছে নিন:",
        "processing": "⚡ {quality} প্রস্তুত হচ্ছে, দয়া করে অপেক্ষা করুন...",
        "uploading": "🚀 টেলিগ্রামে আপলোড হচ্ছে...",
        "custom_prompt": (
            "⏳ আপনি ভিডিওর কোন সময়ের ফ্রেম চান?\n\n"
            "সেকেন্ড বা মিনিট লিখে পাঠান:\n"
            "উদাহরণ: `10` অথবা `01:15`"
        ),
        "custom_success": "✅ ফ্রেম ক্যাপচার সফল ({sec}s)",
        "mid_success": "✅ ভিডিওর মাঝখানের ফ্রেম ({sec}s)",
        "error_frame": "❌ ফ্রেম ক্যাপচার করা সম্ভব হয়নি।",
        "error_expired": "❌ লিঙ্কের মেয়াদ শেষ হয়ে গেছে। অনুগ্রহ করে লিঙ্কটি পুনরায় পাঠান।",
        "error_youtube": "⚠️ ইউটিউব ডাউনলোডের জন্য আলাদা বট নির্ধারিত। এখানে অন্যান্য সোশ্যাল মিডিয়া লিঙ্ক পাঠান।",
        "error_50mb": "⚠️ ফাইলটির সাইজ {size:.1f} MB! টেলিগ্রাম বট লিমিট ৫০ MB ছাড়িয়ে যাওয়ায় পাঠানো সম্ভব নয়।",
        "btn_change_lang": "🌐 ভাষা পরিবর্তন (Language)",
        "highest": "🌟 Highest (1080p)",
        "normal": "🎬 Normal (720p)",
        "fast": "🚀 Fast (Low Size)",
        "doc": "📁 Document Uncompressed",
        "voice": "🎙️ Voice Note (.ogg)",
        "gif": "🎞️ Animated GIF",
        "thumb_hd": "🖼️ Thumb HD",
        "thumb_sd": "🖼️ Thumb Std",
        "mid_frame": "⏱️ Mid Frame",
        "custom_frame": "⏳ Custom Frame"
    },
    "en": {
        "guide": (
            "🌟 **Welcome to Social Media Downloader Bot!** 🌟\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 **Button Guide & Features:**\n\n"
            "🎥 **Video Options:**\n"
            "• `Highest (1080p)`: Maximum available video quality\n"
            "• `Normal (720p)`: Balanced quality & size\n"
            "• `Fast (Low Size)`: Fast download with small file size\n"
            "• `1080p, 720p, 480p, 360p, 240p, 144p`: Specific resolutions\n"
            "• `📁 Document`: Send original file without compression\n\n"
            "🎵 **Audio & Tools:**\n"
            "• `320k, 192k, 128k`: High-fidelity MP3 music tracks\n"
            "• `🎙️ Voice Note`: Native playable voice message\n"
            "• `🎞️ Animated GIF`: Converts clip into a Telegram GIF\n\n"
            "🖼️ **Thumbnails & Frames:**\n"
            "• `Thumb HD / Std`: Original cover picture\n"
            "• `⏱️ Mid Frame`: Screenshot from the exact middle of the video\n"
            "• `⏳ Custom Frame`: Extract any frame by replying with seconds\n\n"
            "💡 **How to use:** Just paste any public video link from TikTok, Facebook, Instagram, X, Reddit, or Pinterest!"
        ),
        "help_text": (
            "📖 **User Guide & Troubleshooting:**\n\n"
            "1️⃣ **Change Language:** Type /lang or 'change language'.\n"
            "2️⃣ **50 MB Limit:** Telegram cannot send files larger than 50 MB. If your video exceeds 50 MB, choose 480p or Fast mode.\n"
            "3️⃣ **Custom Frame:** Click 'Custom Frame' and reply with your timestamp (e.g., 15 or 01:20).\n"
            "4️⃣ **Download Failures:** Make sure the post is public."
        ),
        "help_lang_resp": "🌐 To change your language, click the button below or type /lang:",
        "help_error_resp": (
            "🛠️ **Having trouble downloading?**\n\n"
            "• Ensure the link is public (private accounts are not supported).\n"
            "• If the file is too large, try 720p or 480p.\n"
            "• Try resending the link."
        ),
        "help_size_resp": "ℹ️ Telegram Bot API restricts files to 50 MB max. For long videos, choose 480p or 360p to keep it under 50 MB.",
        "choose_option": "📥 Choose your desired quality or format:",
        "processing": "⚡ Processing {quality}, please wait...",
        "uploading": "🚀 Uploading to Telegram...",
        "custom_prompt": (
            "⏳ Which timestamp frame would you like?\n\n"
            "Reply with seconds or minutes:\n"
            "Example: `10` or `01:15`"
        ),
        "custom_success": "✅ Frame captured successfully ({sec}s)",
        "mid_success": "✅ Middle video frame ({sec}s)",
        "error_frame": "❌ Failed to extract frame.",
        "error_expired": "❌ Link expired. Please send the link again.",
        "error_youtube": "⚠️ YouTube downloads are managed by another bot. Please send links from other platforms.",
        "error_50mb": "⚠️ File size is {size:.1f} MB! Telegram Bot API cannot send files over 50 MB.",
        "btn_change_lang": "🌐 Change Language",
        "highest": "🌟 Highest (1080p)",
        "normal": "🎬 Normal (720p)",
        "fast": "🚀 Fast (Low Size)",
        "doc": "📁 Document Uncompressed",
        "voice": "🎙️ Voice Note (.ogg)",
        "gif": "🎞️ Animated GIF",
        "thumb_hd": "🖼️ Thumb HD",
        "thumb_sd": "🖼️ Thumb Std",
        "mid_frame": "⏱️ Mid Frame",
        "custom_frame": "⏳ Custom Frame"
    }
}

def get_text(user_id, key, **kwargs):
    lang = user_languages.get(user_id, "bn")
    text = TEXTS.get(lang, TEXTS["bn"]).get(key, TEXTS["bn"].get(key, ""))
    return text.format(**kwargs)

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

def extract_frame_ffmpeg(video_source, timestamp_sec, output_img_path):
    cmd = [
        "ffmpeg",
        "-ss", str(timestamp_sec),
        "-i", video_source,
        "-frames:v", "1",
        "-q:v", "2",
        "-y",
        output_img_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return os.path.exists(output_img_path) and os.path.getsize(output_img_path) > 1024

def convert_to_voice_note(input_audio, output_ogg):
    cmd = [
        "ffmpeg",
        "-i", input_audio,
        "-c:a", "libopus",
        "-b:a", "32k",
        "-vbr", "on",
        "-y",
        output_ogg
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return os.path.exists(output_ogg)

def convert_to_gif(input_video, output_gif):
    cmd = [
        "ffmpeg",
        "-t", "10",
        "-i", input_video,
        "-vf", "fps=10,scale=360:-1:flags=lanczos",
        "-y",
        output_gif
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return os.path.exists(output_gif)

def format_caption(title, author, platform, quality, size_mb=None):
    caption = (
        f"🎬 **{title[:65]}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 **Platform:** {platform}\n"
        f"👤 **Author/Channel:** {author}\n"
        f"🎯 **Quality:** {quality}\n"
    )
    if size_mb:
        caption += f"💾 **Size:** {size_mb:.1f} MB\n"
    caption += "━━━━━━━━━━━━━━━━━━━━\n⚡ *Downloaded via Ultra Social Bot*"
    return caption

def build_language_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇧🇩 বাংলা (Bengali)", callback_data="setlang_bn"),
            InlineKeyboardButton("🇺🇸 English", callback_data="setlang_en")
        ]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # শুরুতে সর্বদা দুটি ভাষার অপশন দেওয়া হবে
    await update.message.reply_text(
        "🌐 **Please select your language / আপনার ভাষা নির্বাচন করুন:**",
        reply_markup=build_language_keyboard(),
        parse_mode="Markdown"
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(get_text(user_id, "help_text"), parse_mode="Markdown")

async def cmd_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌐 **Select Language / ভাষা বেছে নিন:**",
        reply_markup=build_language_keyboard(),
        parse_mode="Markdown"
    )

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    lower_text = text.lower()

    if user_id not in user_languages:
        user_languages[user_id] = "bn"

    # কাস্টম ফ্রেমের সময় ইনপুট হ্যান্ডলিং
    if user_id in user_waiting_custom_time:
        saved_url = user_waiting_custom_time.pop(user_id)
        time_input = text.replace("s", "").replace("sec", "").strip()

        try:
            if ":" in time_input:
                parts = time_input.split(":")
                if len(parts) == 2:
                    sec = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                else:
                    sec = int(parts[0])
            else:
                sec = int(time_input)
        except Exception:
            sec = 5

        status_msg = await update.message.reply_text(get_text(user_id, "processing", quality=f"Frame {sec}s"))
        output_dir = "temp_downloads"
        os.makedirs(output_dir, exist_ok=True)
        unique_id = str(uuid.uuid4())[:6]
        output_img = f"{output_dir}/custom_frame_{unique_id}.jpg"

        video_stream_url = None
        if "tiktok.com" in saved_url:
            tk = get_tiktok_direct_url(saved_url)
            if tk:
                video_stream_url = tk.get("video_hd") or tk.get("video_sd")
        else:
            try:
                with yt_dlp.YoutubeDL({'quiet': True, 'format': 'best[ext=mp4]/best'}) as ydl:
                    info = ydl.extract_info(saved_url, download=False)
                    video_stream_url = info.get("url")
            except Exception:
                pass

        if video_stream_url and extract_frame_ffmpeg(video_stream_url, sec, output_img):
            with open(output_img, "rb") as f:
                await update.message.reply_photo(
                    photo=f,
                    caption=get_text(user_id, "custom_success", sec=sec) + "\n⚡ *Ultra Social Bot*",
                    parse_mode="Markdown"
                )
            await status_msg.delete()
            if os.path.exists(output_img):
                os.remove(output_img)
        else:
            await status_msg.edit_text(get_text(user_id, "error_frame"))
        return

    # স্মার্ট অটো-অ্যাসিস্ট্যান্ট নির্দেশিকা
    if not text.startswith("http://") and not text.startswith("https://"):
        if any(w in lower_text for w in ["language", "ভাষা", "bhasha", "change", "পরিবর্তন", "change language"]):
            await update.message.reply_text(
                get_text(user_id, "help_lang_resp"),
                reply_markup=build_language_keyboard()
            )
            return

        if any(w in lower_text for w in ["50mb", "50 mb", "size", "সাইজ", "বড় ফাইল", "limit"]):
            await update.message.reply_text(get_text(user_id, "help_size_resp"))
            return

        if any(w in lower_text for w in ["problem", "error", "সমস্যা", "কাজ করে না", "fail", "not working", "download হচ্ছে না"]):
            await update.message.reply_text(get_text(user_id, "help_error_resp"), parse_mode="Markdown")
            return

        if any(w in lower_text for w in ["help", "নির্দেশনা", "নিয়ম", "faq", "কীভাবে", "কিভাবে"]):
            await update.message.reply_text(get_text(user_id, "help_text"), parse_mode="Markdown")
            return

        await update.message.reply_text(
            "💡 সোশ্যাল মিডিয়ার যেকোনো ভিডিও লিঙ্ক পাঠান অথবা সাহায্য পেতে /help লিখুন।"
        )
        return

    url = text
    if "youtube.com" in url or "youtu.be" in url:
        await update.message.reply_text(get_text(user_id, "error_youtube"))
        return

    user_urls[user_id] = url

    keyboard = [
        [
            InlineKeyboardButton(get_text(user_id, "highest"), callback_data="vid_highest"),
            InlineKeyboardButton(get_text(user_id, "normal"), callback_data="vid_normal"),
            InlineKeyboardButton(get_text(user_id, "fast"), callback_data="vid_fast")
        ],
        [
            InlineKeyboardButton("📺 1080p", callback_data="vid_1080"),
            InlineKeyboardButton("📺 720p", callback_data="vid_720"),
            InlineKeyboardButton("📱 480p", callback_data="vid_480"),
            InlineKeyboardButton("📱 360p", callback_data="vid_360")
        ],
        [
            InlineKeyboardButton("⚡ 240p", callback_data="vid_240"),
            InlineKeyboardButton("⚡ 144p", callback_data="vid_144"),
            InlineKeyboardButton(get_text(user_id, "doc"), callback_data="vid_doc")
        ],
        [
            InlineKeyboardButton("🎵 320k", callback_data="aud_320"),
            InlineKeyboardButton("🎶 192k", callback_data="aud_192"),
            InlineKeyboardButton("📻 128k", callback_data="aud_128")
        ],
        [
            InlineKeyboardButton(get_text(user_id, "voice"), callback_data="aud_voice"),
            InlineKeyboardButton(get_text(user_id, "gif"), callback_data="tool_gif")
        ],
        [
            InlineKeyboardButton(get_text(user_id, "thumb_hd"), callback_data="thumb_hd"),
            InlineKeyboardButton(get_text(user_id, "thumb_sd"), callback_data="thumb_sd"),
            InlineKeyboardButton(get_text(user_id, "mid_frame"), callback_data="frame_mid"),
            InlineKeyboardButton(get_text(user_id, "custom_frame"), callback_data="frame_custom")
        ],
        [
            InlineKeyboardButton(get_text(user_id, "btn_change_lang"), callback_data="cmd_lang")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(get_text(user_id, "choose_option"), reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    # ভাষা বাছাই এবং পরিবর্তন হ্যান্ডলার
    if data == "cmd_lang":
        await query.edit_message_text(
            "🌐 **Select Language / ভাষা বেছে নিন:**",
            reply_markup=build_language_keyboard(),
            parse_mode="Markdown"
        )
        return

    if data.startswith("setlang_"):
        lang_code = data.split("_")[1]
        user_languages[user_id] = lang_code
        # ভাষা সিলেক্ট করার পর সম্পূর্ণ গাইড ও ফিচার তালিকা প্রদর্শন
        await query.edit_message_text(
            get_text(user_id, "guide"),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_text(user_id, "btn_change_lang"), callback_data="cmd_lang")]])
        )
        return

    url = user_urls.get(user_id)
    if not url:
        await query.edit_message_text(get_text(user_id, "error_expired"))
        return

    req_type, quality = data.split("_")
    unique_id = str(uuid.uuid4())[:6]
    output_dir = "temp_downloads"
    os.makedirs(output_dir, exist_ok=True)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    if req_type == "frame" and quality == "custom":
        user_waiting_custom_time[user_id] = url
        await query.edit_message_text(get_text(user_id, "custom_prompt"), parse_mode="Markdown")
        return

    if req_type == "frame" and quality == "mid":
        status_msg = await query.edit_message_text(get_text(user_id, "processing", quality="Mid Frame"))
        output_img = f"{output_dir}/mid_frame_{unique_id}.jpg"
        target_stream = None
        duration = 10

        if "tiktok.com" in url:
            tk = get_tiktok_direct_url(url)
            if tk:
                target_stream = tk.get("video_hd") or tk.get("video_sd")
                duration = tk.get("duration", 10)
        else:
            try:
                with yt_dlp.YoutubeDL({'quiet': True, 'format': 'best[ext=mp4]/best'}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    target_stream = info.get("url")
                    duration = info.get("duration", 10)
            except Exception:
                pass

        mid_point = max(1, int(duration // 2))
        if target_stream and extract_frame_ffmpeg(target_stream, mid_point, output_img):
            with open(output_img, "rb") as f:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=f,
                    caption=get_text(user_id, "mid_success", sec=mid_point) + "\n⚡ *Ultra Social Bot*",
                    parse_mode="Markdown"
                )
            await status_msg.delete()
            if os.path.exists(output_img):
                os.remove(output_img)
        else:
            await status_msg.edit_text(get_text(user_id, "error_frame"))
        return

    quality_display = quality.upper()
    status_msg = await query.edit_message_text(get_text(user_id, "processing", quality=quality_display))

    platform_name = "Social Media"
    if "tiktok.com" in url: platform_name = "TikTok"
    elif "instagram.com" in url: platform_name = "Instagram"
    elif "facebook.com" in url or "fb.watch" in url: platform_name = "Facebook"
    elif "twitter.com" in url or "x.com" in url: platform_name = "Twitter (X)"
    elif "reddit.com" in url: platform_name = "Reddit"
    elif "pinterest.com" in url or "pin.it" in url: platform_name = "Pinterest"

    # ১. টিকটক ইঞ্জিন
    if "tiktok.com" in url and req_type not in ["tool"]:
        tk_data = get_tiktok_direct_url(url)
        if tk_data:
            file_path = None
            thumb_path = None
            try:
                if req_type == "thumb":
                    target_url = tk_data["cover_hd"] if quality == "hd" else tk_data["cover_sd"]
                    file_path = f"{output_dir}/tk_thumb_{unique_id}.jpg"
                    r = requests.get(target_url, headers=headers, timeout=20)
                    with open(file_path, "wb") as f:
                        f.write(r.content)
                    
                    await status_msg.edit_text(get_text(user_id, "uploading"))
                    with open(file_path, "rb") as f:
                        await context.bot.send_photo(
                            chat_id=user_id,
                            photo=f,
                            caption=format_caption(tk_data['title'], tk_data['author'], "TikTok", quality_display),
                            parse_mode="Markdown"
                        )
                    await status_msg.delete()
                    return

                if req_type == "vid":
                    target_url = tk_data["video_hd"] if quality in ["highest", "1080", "720", "doc"] else tk_data["video_sd"]
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

                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                if file_size_mb > 50:
                    await status_msg.edit_text(get_text(user_id, "error_50mb", size=file_size_mb))
                    return

                if tk_data.get("cover_sd"):
                    thumb_path = f"{output_dir}/thumb_{unique_id}.jpg"
                    tr = requests.get(tk_data["cover_sd"], headers=headers, timeout=15)
                    with open(thumb_path, "wb") as tf:
                        tf.write(tr.content)

                await status_msg.edit_text(get_text(user_id, "uploading"))

                if req_type == "aud" and quality == "voice":
                    ogg_path = f"{output_dir}/voice_{unique_id}.ogg"
                    if convert_to_voice_note(file_path, ogg_path):
                        with open(ogg_path, "rb") as vf:
                            await context.bot.send_voice(
                                chat_id=user_id,
                                voice=vf,
                                caption=f"🎙️ {tk_data['title'][:50]}\n⚡ *Ultra Social Bot*",
                                parse_mode="Markdown"
                            )
                        if os.path.exists(ogg_path):
                            os.remove(ogg_path)
                    await status_msg.delete()
                    return

                with open(file_path, "rb") as f:
                    if req_type == "vid":
                        if quality == "doc":
                            await context.bot.send_document(
                                chat_id=user_id,
                                document=f,
                                caption=format_caption(tk_data['title'], tk_data['author'], "TikTok", quality_display, file_size_mb),
                                parse_mode="Markdown"
                            )
                        else:
                            await context.bot.send_video(
                                chat_id=user_id,
                                video=f,
                                supports_streaming=True,
                                caption=format_caption(tk_data['title'], tk_data['author'], "TikTok", quality_display, file_size_mb),
                                parse_mode="Markdown"
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
                await context.bot.send_message(chat_id=user_id, text=f"Error: {str(e)[:100]}")
                return
            finally:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                if thumb_path and os.path.exists(thumb_path):
                    os.remove(thumb_path)

    # ২. অন্যান্য প্ল্যাটফর্ম
    output_template = f"{output_dir}/media_{unique_id}.%(ext)s"

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
                uploader = info.get('uploader', 'Creator')
                thumb_url = info.get('thumbnail')

                if quality == "hd" and info.get('thumbnails'):
                    thumb_url = info['thumbnails'][-1].get('url', thumb_url)

                if thumb_url:
                    file_path = f"{output_dir}/thumb_{unique_id}.jpg"
                    r = requests.get(thumb_url, headers=headers, timeout=20)
                    with open(file_path, "wb") as f:
                        f.write(r.content)

            if file_path and os.path.exists(file_path):
                await status_msg.edit_text(get_text(user_id, "uploading"))
                with open(file_path, "rb") as f:
                    await context.bot.send_photo(
                        chat_id=user_id,
                        photo=f,
                        caption=format_caption(video_title, uploader, platform_name, quality_display),
                        parse_mode="Markdown"
                    )
                await status_msg.delete()
            else:
                await status_msg.edit_text(get_text(user_id, "error_frame"))
        except Exception as e:
            await context.bot.send_message(chat_id=user_id, text=f"Error: {str(e)[:150]}")
        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        return

    if req_type in ["vid", "tool"]:
        if quality == "highest" or quality == "doc":
            format_opt = "bestvideo+bestaudio/best"
        elif quality == "normal":
            format_opt = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
        elif quality == "fast" or quality == "gif":
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
            if req_type in ["vid", "tool"]:
                if os.path.exists(base_name + ".mp4"):
                    file_path = base_name + ".mp4"
            else:
                if os.path.exists(base_name + ".mp3"):
                    file_path = base_name + ".mp3"

        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 50:
            await status_msg.edit_text(get_text(user_id, "error_50mb", size=file_size_mb))
            return

        if req_type == "tool" and quality == "gif":
            await status_msg.edit_text(get_text(user_id, "processing", quality="GIF"))
            gif_path = f"{output_dir}/gif_{unique_id}.gif"
            if convert_to_gif(file_path, gif_path):
                with open(gif_path, "rb") as gf:
                    await context.bot.send_animation(
                        chat_id=user_id,
                        animation=gf,
                        caption=f"🎞️ {video_title[:50]}\n⚡ *Ultra Social Bot*",
                        parse_mode="Markdown"
                    )
                if os.path.exists(gif_path):
                    os.remove(gif_path)
                await status_msg.delete()
                return

        if req_type == "aud" and quality == "voice":
            await status_msg.edit_text(get_text(user_id, "processing", quality="Voice Note"))
            ogg_path = f"{output_dir}/voice_{unique_id}.ogg"
            if convert_to_voice_note(file_path, ogg_path):
                with open(ogg_path, "rb") as vf:
                    await context.bot.send_voice(
                        chat_id=user_id,
                        voice=vf,
                        caption=f"🎙️ {video_title[:50]}\n⚡ *Ultra Social Bot*",
                        parse_mode="Markdown"
                    )
                if os.path.exists(ogg_path):
                    os.remove(ogg_path)
                await status_msg.delete()
                return

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

        await status_msg.edit_text(get_text(user_id, "uploading"))

        with open(file_path, 'rb') as f:
            if req_type == "vid":
                if quality == "doc":
                    await context.bot.send_document(
                        chat_id=user_id,
                        document=f,
                        caption=format_caption(video_title, channel_name, platform_name, quality_display, file_size_mb),
                        parse_mode="Markdown"
                    )
                else:
                    await context.bot.send_video(
                        chat_id=user_id,
                        video=f,
                        supports_streaming=True,
                        caption=format_caption(video_title, channel_name, platform_name, quality_display, file_size_mb),
                        parse_mode="Markdown"
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
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("lang", cmd_language))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("Ultra Simple Dual-Language Social Media Bot is Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
