import os
import io
import threading
import uuid
import logging
import subprocess
import requests
import re
import static_ffmpeg
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
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
import instaloader
from PIL import Image

# FFmpeg সচল করা
static_ffmpeg.add_paths()

# Render Web Service 24/7 লাইভ রাখার Flask সার্ভার
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Ultra 4K/2K Social Downloader Bot with Guaranteed Photo Fix is Running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# আপনার নতুন বটের API টোকেন
BOT_TOKEN = "8739008151:AAFL3n3Q16U6mPuw5YCo1z635hIplMHy3l4"

# ডাটা ডিকশনারি
user_urls = {}
user_waiting_custom_time = {}
user_waiting_gif_time = {}
user_waiting_audio_trim = {}
user_languages = {}
user_quick_mode = {}

# Instaloader ইঞ্জিন সেটআপ
L = instaloader.Instaloader(
    download_pictures=False,
    download_videos=False,
    download_video_thumbnails=False,
    download_geotags=False,
    download_comments=False,
    save_metadata=False,
    compress_json=False
)

TEXTS = {
    "bn": {
        "guide": (
            "🌟 আল্টিমেট ৪K সোশ্যাল মিডিয়া ডাউনলোডার 🌟\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 সহজ ব্যবহারের নিয়মাবলী:\n"
            "যেকোনো ভিডিও বা ছবির পোস্ট লিঙ্ক সরাসরি চ্যাটে পাঠিয়ে দিন (TikTok, Instagram, Facebook, X, Reddit, Pinterest)।\n\n"
            "🎥 ভিডিও কোয়ালিটি: Highest, Medium, Lowest, Fast ও ডকুমেন্ট মোড এবং কাস্টম রেজোলিউশন (4K থেকে 144p)\n"
            "🖼️ ছবি ও স্লাইড: Instagram ও TikTok-এর সব ছবি একসাথে ফুল রেজোলিউশনে অ্যালবাম আকারে ডাউনলোড!\n"
            "🎞️ GIF ও স্পিড টুলস: অটো GIF, কাস্টম ট্রিমড GIF ও ভিডিও প্লেব্যাক স্পিড (0.5x, 1.5x, 2x)\n"
            "🎵 অডিও: 320k, 192k, 128k, রিংটোন মেকার ও ভয়েস মেসেজ\n"
            "🗜️ স্মার্ট কম্প্রেশন: বড় ফাইল (৫০ MB+) হলে কোয়ালিটি ঠিক রেখে স্বয়ংক্রিয়ভাবে অপ্টিমাইজ হয়ে যাবে!"
        ),
        "help_text": (
            "📖 জরুরি নির্দেশিকা ও কমান্ডসমূহ:\n\n"
            "1️⃣ /quick : সরাসরি 720p ইনস্ট্যান্ট ডাউনলোড মোড অন/অফ করতে।\n"
            "2️⃣ /lang : ভাষা (বাংলা / English) পরিবর্তন করতে।\n"
            "3️⃣ কাস্টম রেজোলিউশন: ভিডিও অপশনে গিয়ে 'কাস্টম রেজোলিউশন' চাপলে 4K, 2K, 1080p সহ সব সাইজ দেখতে পাবেন।\n"
            "4️⃣ ৫০ MB লিমিট: ৪K/২K ভিডিও ৫০ MB ছাড়ালে বট স্বয়ংক্রিয়ভাবে কোয়ালিটি অক্ষুণ্ণ রেখে সাইজ কমিয়ে পাঠাবে।"
        ),
        "help_lang_resp": "🌐 ভাষা পরিবর্তন করতে নিচের বাটনে চাপ দিন অথবা /lang লিখুন:",
        "help_error_resp": "🛠️ লিঙ্কটি পাবলিক কি না চেক করুন এবং কোনো প্রাইভেট গ্রুপ বা প্রোফাইল নয় তা নিশ্চিত করুন।",
        "help_size_resp": "ℹ️️ টেলিগ্রাম বটে সর্বোচ্চ ৫০ MB ফাইল পাঠানো যায়। এর চেয়ে বড় ভিডিও হলে বট নিজেই তা স্বয়ংক্রিয়ভাবে অপ্টিমাইজ করে পাঠাবে।",
        "choose_main": "📥 আপনি কী ডাউনলোড করতে চান? ক্যাটাগরি বেছে নিন:",
        "choose_video": "🎥 আপনার পছন্দের ভিডিও মোড বেছে নিন:",
        "choose_custom_res": "🎯 নির্দিষ্ট রেজোলিউশন বেছে নিন (4K থেকে 144p):",
        "choose_audio": "🎵 আপনার পছন্দের অডিও ফরম্যাট বেছে নিন:",
        "choose_gif_tools": "🎞️ আপনার পছন্দের GIF বা স্পিড টুল বেছে নিন:",
        "choose_thumb": "🖼️ আপনার পছন্দের ছবি বা ফ্রেম অপশন বেছে নিন:",
        "choose_speed": "⏩ ভিডিওর প্লেব্যাক স্পিড বেছে নিন:",
        "processing": "⚡ {quality} প্রস্তুত হচ্ছে, দয়া করে অপেক্ষা করুন...",
        "compressing": "🗜️ ফাইল সাইজ ৫০ MB ছাড়িয়েছে, কোয়ালিটি ঠিক রেখে অপ্টিমাইজ করা হচ্ছে...",
        "uploading": "🚀 টেলিগ্রামে আপলোড হচ্ছে...",
        "custom_prompt": "⏳ ভিডিওর কোন সেকেন্ডের ফ্রেম চান? লিখে পাঠান (উদা: 10 বা 01:15):",
        "gif_prompt": "🎞️️ GIF-এর শুরু ও শেষের সময় লিখে পাঠান (উদা: 5-10 বা 00:10-00:15, সর্বোচ্চ ১০ সেকেন্ড):",
        "audio_trim_prompt": "✂️ রিংটোনের শুরু ও শেষের সময় লিখে পাঠান (উদা: 0-30 বা 00:20-00:50, সর্বোচ্চ ৬০ সেকেন্ড):",
        "gif_limit_error": "⚠️ GIF তৈরির রেঞ্জ সর্বোচ্চ ১০ সেকেন্ড হতে হবে (যেমন: 5-12)। আবার চেষ্টা করুন।",
        "audio_limit_error": "⚠️ রিংটোনের রেঞ্জ সর্বোচ্চ ৬০ সেকেন্ড হতে হবে (যেমন: 0-30)। আবার চেষ্টা করুন।",
        "custom_success": "✅ ফ্রেম ক্যাপচার সফল ({sec}s)",
        "mid_success": "✅ ভিডিওর মাঝখানের ফ্রেম ({sec}s)",
        "error_frame": "❌ ফ্রেম ক্যাপচার করা সম্ভব হয়নি।",
        "error_expired": "❌ লিঙ্কের মেয়াদ শেষ হয়ে গেছে। লিঙ্কটি পুনরায় পাঠান।",
        "error_youtube": "⚠️ ইউটিউব ডাউনলোডের জন্য আলাদা বট নির্ধারিত। এখানে অন্যান্য সোশ্যাল লিঙ্ক পাঠান।",
        "error_compress": "⚠️ ভিডিওটি অতিরিক্ত বড় হওয়ায় ৫০ MB-র মধ্যে কম্প্রেস করা সম্ভব হয়নি। কম রেজোলিউশন (720p/480p) বেছে নিন।",
        "btn_video": "🎥 Video Options",
        "btn_audio": "🎵 Audio & Ringtone",
        "btn_gif_tools": "🎞️ GIF & Video Tools",
        "btn_thumb": "🖼️ Photos & Thumbnails",
        "btn_speed": "⏩ Change Video Speed",
        "btn_custom_res": "🎯 কাস্টম রেজোলিউশন (4K, 2K, 1080p...)",
        "btn_back": "🔙 Back (প্রধান মেনু)",
        "btn_back_video": "🔙 Back (ভিডিও মেনু)",
        "btn_cancel": "❌ Cancel",
        "vid_4k": "👑 4K Ultra HD (2160p)",
        "vid_2k": "💎 2K Quad HD (1440p)",
        "highest": "🌟 Highest Download",
        "normal": "🎬 Medium Download",
        "lowest": "⚡ Lowest Download",
        "fast": "🚀 Fast Mode (Quick)",
        "doc": "📁 Document Uncompressed",
        "voice": "🎙️ Voice Note (.ogg)",
        "gif_auto": "🎞️ Auto GIF (১-ক্লিক)",
        "gif_custom": "⏳ Custom GIF (টাইম ট্রিম)",
        "ringtone": "✂️ Audio Trim / Ringtone",
        "thumb_hd": "🖼️ HD Cover Photo",
        "thumb_sd": "🖼️️ Standard Cover",
        "mid_frame": "⏱️ Mid Frame",
        "custom_frame": "⏳ Custom Frame",
        "all_photos": "📸 সব ছবি একসাথে নামান (All Photos)",
        "multi_all": "📦 সব ছবি ও ভিডিও একসাথে (Album)",
        "multi_first": "🖼️ শুধুমাত্র ১ম ছবি/ভিডিও (First One)"
    },
    "en": {
        "guide": (
            "🌟 Ultimate 4K Social Media Downloader 🌟\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 How to use:\n"
            "Send any public video or photo post link from TikTok, Instagram, Facebook, X, Reddit, or Pinterest!\n\n"
            "🎥 Video Quality: Highest, Medium, Lowest, Fast, Document & Custom Resolutions (4K to 144p)\n"
            "🖼️ Photos: Full-resolution album download for Instagram & TikTok carousels!\n"
            "🎞️ GIF & Speed Tools: Auto GIF, Custom Trimmed GIF & Speed Changer (0.5x, 1.5x, 2x)\n"
            "🎵 Audio: 320k, 192k, 128k, Ringtone Trimmer & Voice Notes\n"
            "🗜️ Smart Compression: Videos exceeding 50 MB are automatically optimized under 50 MB!"
        ),
        "help_text": (
            "📖 User Guide & Commands:\n\n"
            "1️⃣ /quick : Toggle instant 720p quick download mode.\n"
            "2️⃣ /lang : Change language (English / Bengali).\n"
            "3️⃣ Custom Resolutions: Go to Video Options and tap 'Custom Resolutions' to choose 4K, 2K, 1080p, etc.\n"
            "4️⃣ 50 MB Limit: Files over 50 MB are automatically compressed preserving high quality."
        ),
        "help_lang_resp": "🌐 To change your language, click below or type /lang:",
        "help_error_resp": "🛠️ Ensure the post is public and not from a private account.",
        "help_size_resp": "ℹ️ Telegram Bot API limits files to 50 MB max. Large videos are automatically compressed.",
        "choose_main": "📥 What would you like to download? Choose a category:",
        "choose_video": "🎥 Choose your desired video mode:",
        "choose_custom_res": "🎯 Choose specific resolution (4K to 144p):",
        "choose_audio": "🎵 Choose your audio format:",
        "choose_gif_tools": "🎞️ Choose GIF or video speed tools:",
        "choose_thumb": "🖼️ Choose your photo, cover, or frame option:",
        "choose_speed": "⏩ Choose playback speed:",
        "processing": "⚡ Processing {quality}, please wait...",
        "compressing": "🗜️ File exceeds 50 MB, optimizing under 50 MB without quality loss...",
        "uploading": "🚀 Uploading to Telegram...",
        "custom_prompt": "⏳ Reply with frame timestamp (e.g. 10 or 01:15):",
        "gif_prompt": "🎞️ Reply with start and end time (e.g. 5-10 or 00:10-00:15, max 10s):",
        "audio_trim_prompt": "✂️ Reply with start and end time (e.g. 0-30 or 00:20-00:50, max 60s):",
        "gif_limit_error": "⚠️ GIF range must be 10 seconds or less. Please try again.",
        "audio_limit_error": "⚠️ Ringtone range must be 60 seconds or less. Please try again.",
        "custom_success": "✅ Frame captured successfully ({sec}s)",
        "mid_success": "✅ Middle video frame ({sec}s)",
        "error_frame": "❌ Failed to extract frame.",
        "error_expired": "❌ Link expired. Please send the link again.",
        "error_youtube": "⚠️ YouTube downloads are managed separately. Please send links from other platforms.",
        "error_compress": "⚠️ File was too large to fit in 50 MB cleanly. Please select a lower resolution (720p/480p).",
        "btn_video": "🎥 Video Options",
        "btn_audio": "🎵 Audio & Ringtone",
        "btn_gif_tools": "🎞️ GIF & Video Tools",
        "btn_thumb": "🖼️️ Photos & Thumbnails",
        "btn_speed": "⏩ Change Video Speed",
        "btn_custom_res": "🎯 Custom Resolutions (4K, 2K, 1080p...)",
        "btn_back": "🔙 Back to Main Menu",
        "btn_back_video": "🔙 Back to Video Menu",
        "btn_cancel": "❌ Cancel",
        "vid_4k": "👑 4K Ultra HD (2160p)",
        "vid_2k": "💎 2K Quad HD (1440p)",
        "highest": "🌟 Highest Download",
        "normal": "🎬 Medium Download",
        "lowest": "⚡ Lowest Download",
        "fast": "🚀 Fast Mode (Quick)",
        "doc": "📁 Document Uncompressed",
        "voice": "🎙️ Voice Note (.ogg)",
        "gif_auto": "🎞️ Auto GIF (Instant)",
        "gif_custom": "⏳ Custom GIF (Trim)",
        "ringtone": "✂️ Audio Trim / Ringtone",
        "thumb_hd": "🖼️ HD Cover Photo",
        "thumb_sd": "🖼️ Standard Cover",
        "mid_frame": "⏱️ Mid Frame",
        "custom_frame": "⏳ Custom Frame",
        "all_photos": "📸 Download All Photos (Album)",
        "multi_all": "📦 Download All Photos/Videos (Album)",
        "multi_first": "🖼️ Download First Media Only"
    }
}

def get_text(user_id, key, **kwargs):
    lang = user_languages.get(user_id, "bn")
    text = TEXTS.get(lang, TEXTS["bn"]).get(key, TEXTS["bn"].get(key, ""))
    return text.format(**kwargs)

def parse_time_str(t_str):
    t_str = t_str.strip().replace("s", "").replace("sec", "")
    if ":" in t_str:
        p = t_str.split(":")
        if len(p) == 2:
            return int(p[0]) * 60 + int(p[1])
        elif len(p) == 3:
            return int(p[0]) * 3600 + int(p[1]) * 60 + int(p[2])
    return int(t_str)

def get_tiktok_details(tiktok_url):
    try:
        api_url = f"https://tikwm.com/api/?url={tiktok_url}"
        res = requests.get(api_url, timeout=15).json()
        if res.get("code") == 0:
            data = res.get("data", {})
            return {
                "title": data.get("title", "TikTok Media"),
                "video_hd": data.get("hdplay") or data.get("play"),
                "video_sd": data.get("play"),
                "audio_url": data.get("music"),
                "cover_hd": data.get("origin_cover") or data.get("cover"),
                "cover_sd": data.get("cover"),
                "images": data.get("images") or [],
                "author": data.get("author", {}).get("nickname", "TikTok Creator"),
                "duration": data.get("duration", 0)
            }
    except Exception:
        pass
    return None

def extract_instagram_media_robust(url):
    media_list = []
    shortcode_match = re.search(r'/(?:p|reel|tv)/([A-Za-z0-9_-]+)', url)
    if shortcode_match:
        shortcode = shortcode_match.group(1)
        try:
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            if post.typename == 'GraphSidecar':
                for node in post.get_sidecar_nodes():
                    if node.is_video:
                        media_list.append((node.video_url, "video"))
                    else:
                        media_list.append((node.display_url, "image"))
            else:
                if post.is_video:
                    media_list.append((post.video_url, "video"))
                else:
                    media_list.append((post.url, "image"))
            if media_list:
                return media_list
        except Exception:
            pass

    try:
        clean_url = url.split("?")[0].rstrip("/")
        api_url = f"https://api.vkrdown.com/insta/?url={clean_url}"
        res = requests.get(api_url, timeout=12).json()
        if res.get("status") == "success" and res.get("data"):
            for item in res["data"]:
                m_url = item.get("url") or item.get("download_url")
                m_type = "video" if (".mp4" in m_url.lower() or item.get("type") == "video") else "image"
                media_list.append((m_url, m_type))
            if media_list:
                return media_list
    except Exception:
        pass

    return media_list

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

def trim_audio_ffmpeg(input_file, output_mp3, start_sec, duration):
    cmd = [
        "ffmpeg",
        "-ss", str(start_sec),
        "-t", str(duration),
        "-i", input_file,
        "-c:a", "libmp3lame",
        "-q:a", "2",
        "-y",
        output_mp3
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return os.path.exists(output_mp3) and os.path.getsize(output_mp3) > 1024

def convert_to_gif_mp4(input_video, output_mp4, start_sec=0, duration=7):
    cmd = [
        "ffmpeg",
        "-ss", str(start_sec),
        "-t", str(duration),
        "-i", input_video,
        "-an",
        "-vf", "scale='min(480,iw)':-2",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-profile:v", "baseline",
        "-level", "3.0",
        "-movflags", "+faststart",
        "-y",
        output_mp4
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 1024

def change_video_speed_ffmpeg(input_video, output_video, speed=1.5):
    v_pts = 1.0 / speed
    if speed == 0.5:
        a_filter = "atempo=0.5"
    elif speed == 1.5:
        a_filter = "atempo=1.5"
    elif speed == 2.0:
        a_filter = "atempo=2.0"
    else:
        a_filter = "atempo=1.0"

    cmd = [
        "ffmpeg",
        "-i", input_video,
        "-filter_complex", f"[0:v]setpts={v_pts}*PTS[v];[0:a]{a_filter}[a]",
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-y",
        output_video
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return os.path.exists(output_video) and os.path.getsize(output_video) > 1024

def compress_video_under_50mb(input_video, output_video, duration=None):
    try:
        if not duration or duration <= 0:
            cmd_dur = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", input_video
            ]
            res = subprocess.run(cmd_dur, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            duration = float(res.stdout.strip())
    except Exception:
        duration = 60.0

    target_size_bytes = 47.0 * 1024 * 1024 * 8
    audio_bitrate_kb = 128
    audio_bits = audio_bitrate_kb * 1024 * duration
    video_bits = target_size_bytes - audio_bits
    video_bitrate_kb = int(max(video_bits / duration / 1024, 250))

    cmd = [
        "ffmpeg",
        "-i", input_video,
        "-c:v", "libx264",
        "-b:v", f"{video_bitrate_kb}k",
        "-maxrate", f"{int(video_bitrate_kb * 1.3)}k",
        "-bufsize", f"{int(video_bitrate_kb * 2)}k",
        "-preset", "ultrafast",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-y",
        output_video
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(output_video):
        size_mb = os.path.getsize(output_video) / (1024 * 1024)
        return size_mb <= 49.5
    return False

def format_caption(title, author, platform, quality, size_mb=None, was_compressed=False):
    # কোনো ধরনের এরর ছাড়া ক্লিন ক্যাপশন
    safe_title = title.replace("\n", " ").strip()[:65]
    safe_author = author.replace("\n", " ").strip()[:30]
    caption = (
        f"🎬 {safe_title}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 Platform: {platform}\n"
        f"👤 Author/Channel: {safe_author}\n"
        f"🎯 Quality: {quality}\n"
    )
    if size_mb:
        caption += f"💾 Size: {size_mb:.1f} MB\n"
    if was_compressed:
        caption += "🗜️ Smart 50MB Auto-Compressed (High Quality)\n"
    caption += "━━━━━━━━━━━━━━━━━━━━\n⚡ Downloaded via Ultra Social Bot"
    return caption

def build_language_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇧🇩 বাংলা (Bengali)", callback_data="setlang_bn"),
            InlineKeyboardButton("🇺🇸 English", callback_data="setlang_en")
        ]
    ])

def get_main_menu(user_id, has_multi=False):
    keyboard = []
    if has_multi:
        keyboard.append([
            InlineKeyboardButton(get_text(user_id, "multi_all"), callback_data="multi_all"),
            InlineKeyboardButton(get_text(user_id, "multi_first"), callback_data="multi_first")
        ])
    keyboard.extend([
        [InlineKeyboardButton(get_text(user_id, "btn_video"), callback_data="cat_video")],
        [InlineKeyboardButton(get_text(user_id, "btn_audio"), callback_data="cat_audio")],
        [InlineKeyboardButton(get_text(user_id, "btn_gif_tools"), callback_data="cat_gif_tools")],
        [InlineKeyboardButton(get_text(user_id, "btn_thumb"), callback_data="cat_thumb")],
        [InlineKeyboardButton(get_text(user_id, "btn_cancel"), callback_data="cat_cancel")]
    ])
    return InlineKeyboardMarkup(keyboard)

def get_video_menu(user_id):
    keyboard = [
        [
            InlineKeyboardButton(get_text(user_id, "highest"), callback_data="vid_highest"),
            InlineKeyboardButton(get_text(user_id, "normal"), callback_data="vid_normal"),
            InlineKeyboardButton(get_text(user_id, "lowest"), callback_data="vid_lowest")
        ],
        [
            InlineKeyboardButton(get_text(user_id, "fast"), callback_data="vid_fast"),
            InlineKeyboardButton(get_text(user_id, "doc"), callback_data="vid_doc")
        ],
        [
            InlineKeyboardButton(get_text(user_id, "btn_custom_res"), callback_data="cat_custom_res")
        ],
        [
            InlineKeyboardButton(get_text(user_id, "btn_back"), callback_data="cat_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_custom_res_menu(user_id):
    keyboard = [
        [
            InlineKeyboardButton(get_text(user_id, "vid_4k"), callback_data="vid_2160"),
            InlineKeyboardButton(get_text(user_id, "vid_2k"), callback_data="vid_1440")
        ],
        [
            InlineKeyboardButton("📺 1080p", callback_data="vid_1080"),
            InlineKeyboardButton("📺 720p", callback_data="vid_720")
        ],
        [
            InlineKeyboardButton("📱 480p", callback_data="vid_480"),
            InlineKeyboardButton("📱 360p", callback_data="vid_360")
        ],
        [
            InlineKeyboardButton("⚡ 240p", callback_data="vid_240"),
            InlineKeyboardButton("⚡ 144p", callback_data="vid_144")
        ],
        [
            InlineKeyboardButton(get_text(user_id, "btn_back_video"), callback_data="cat_video")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_gif_tools_menu(user_id):
    keyboard = [
        [
            InlineKeyboardButton(get_text(user_id, "gif_auto"), callback_data="tool_gifauto"),
            InlineKeyboardButton(get_text(user_id, "gif_custom"), callback_data="tool_gifcustom")
        ],
        [
            InlineKeyboardButton(get_text(user_id, "btn_speed"), callback_data="cat_speed")
        ],
        [
            InlineKeyboardButton(get_text(user_id, "btn_back"), callback_data="cat_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_speed_menu(user_id):
    keyboard = [
        [
            InlineKeyboardButton("🐌 0.5x Slow", callback_data="spd_0.5"),
            InlineKeyboardButton("⚡ 1.5x Fast", callback_data="spd_1.5"),
            InlineKeyboardButton("🚀 2.0x Double", callback_data="spd_2.0")
        ],
        [
            InlineKeyboardButton(get_text(user_id, "btn_back"), callback_data="cat_gif_tools")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_audio_menu(user_id):
    keyboard = [
        [
            InlineKeyboardButton("🎵 MP3 320k", callback_data="aud_320"),
            InlineKeyboardButton("🎶 MP3 192k", callback_data="aud_192"),
            InlineKeyboardButton("📻 MP3 128k", callback_data="aud_128")
        ],
        [
            InlineKeyboardButton(get_text(user_id, "ringtone"), callback_data="tool_audiotrim"),
            InlineKeyboardButton(get_text(user_id, "voice"), callback_data="aud_voice")
        ],
        [
            InlineKeyboardButton(get_text(user_id, "btn_back"), callback_data="cat_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_thumb_menu(user_id, has_photos=False):
    keyboard = []
    if has_photos:
        keyboard.append([InlineKeyboardButton(get_text(user_id, "all_photos"), callback_data="all_photos_dl")])
    keyboard.extend([
        [
            InlineKeyboardButton(get_text(user_id, "thumb_hd"), callback_data="thumb_hd"),
            InlineKeyboardButton(get_text(user_id, "thumb_sd"), callback_data="thumb_sd")
        ],
        [
            InlineKeyboardButton(get_text(user_id, "mid_frame"), callback_data="frame_mid"),
            InlineKeyboardButton(get_text(user_id, "custom_frame"), callback_data="frame_custom")
        ],
        [
            InlineKeyboardButton(get_text(user_id, "btn_back"), callback_data="cat_main")
        ]
    ])
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌐 Please select your language / আপনার ভাষা নির্বাচন করুন:",
        reply_markup=build_language_keyboard()
    )

async def cmd_quick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current_state = user_quick_mode.get(user_id, False)
    user_quick_mode[user_id] = not current_state
    state_str = "চালু (ON) ⚡" if not current_state else "বন্ধ (OFF) 🛑"
    await update.message.reply_text(
        f"⚡ Quick Download Mode: {state_str}\n"
        "এটি চালু থাকলে লিঙ্ক দেওয়ার সাথে সাথে কোনো মেনু ছাড়াই সরাসরি 720p সেরা কোয়ালিটিতে ভিডিও ডাউনলোড হবে।"
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(get_text(user_id, "help_text"))

async def cmd_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌐 Select Language / ভাষা বেছে নিন:",
        reply_markup=build_language_keyboard()
    )

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    lower_text = text.lower()

    if user_id not in user_languages:
        user_languages[user_id] = "bn"

    output_dir = "temp_downloads"
    os.makedirs(output_dir, exist_ok=True)

    if user_id in user_waiting_audio_trim:
        saved_url = user_waiting_audio_trim.pop(user_id)
        start_sec, end_sec = 0, 30
        try:
            if "-" in text:
                parts = text.split("-")
                start_sec = parse_time_str(parts[0])
                end_sec = parse_time_str(parts[1])
            else:
                start_sec = parse_time_str(text)
                end_sec = start_sec + 30
        except Exception:
            start_sec, end_sec = 0, 30

        duration = max(1, end_sec - start_sec)
        if duration > 60:
            await update.message.reply_text(get_text(user_id, "audio_limit_error"))
            user_waiting_audio_trim[user_id] = saved_url
            return

        status_msg = await update.message.reply_text(get_text(user_id, "processing", quality=f"Ringtone ({start_sec}s - {end_sec}s)"))
        unique_id = str(uuid.uuid4())[:6]
        raw_audio = f"{output_dir}/raw_aud_{unique_id}.mp3"
        trimmed_mp3 = f"{output_dir}/ringtone_{unique_id}.mp3"

        try:
            ydl_opts = {
                'outtmpl': f"{output_dir}/aud_{unique_id}.%(ext)s",
                'format': 'bestaudio/best',
                'quiet': True,
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}]
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(saved_url, download=True)
                title = info.get('title', 'Ringtone')
                artist = info.get('uploader', 'Music')
                raw_audio = f"{output_dir}/aud_{unique_id}.mp3"

            if trim_audio_ffmpeg(raw_audio, trimmed_mp3, start_sec, duration):
                with open(trimmed_mp3, "rb") as rf:
                    await context.bot.send_audio(
                        chat_id=user_id,
                        audio=rf,
                        title=f"{title[:35]} (Ringtone)",
                        performer=artist[:25],
                        duration=duration,
                        caption=f"✂️ Ringtone: {start_sec}s - {end_sec}s\n⚡ Ultra Social Bot"
                    )
                await status_msg.delete()
            else:
                await status_msg.edit_text("❌ রিংটোন তৈরি করা সম্ভব হয়নি।")
        except Exception as e:
            await status_msg.edit_text(f"Audio Error: {str(e)[:100]}")
        finally:
            for f in [raw_audio, trimmed_mp3]:
                if os.path.exists(f): os.remove(f)
        return

    if user_id in user_waiting_gif_time:
        saved_url = user_waiting_gif_time.pop(user_id)
        start_sec, end_sec = 0, 7
        try:
            if "-" in text:
                parts = text.split("-")
                start_sec = parse_time_str(parts[0])
                end_sec = parse_time_str(parts[1])
            else:
                start_sec = parse_time_str(text)
                end_sec = start_sec + 7
        except Exception:
            start_sec, end_sec = 0, 7

        duration = max(1, end_sec - start_sec)
        if duration > 10:
            await update.message.reply_text(get_text(user_id, "gif_limit_error"))
            user_waiting_gif_time[user_id] = saved_url
            return

        status_msg = await update.message.reply_text(get_text(user_id, "processing", quality=f"Custom GIF ({start_sec}s - {end_sec}s)"))
        unique_id = str(uuid.uuid4())[:6]
        raw_video = f"{output_dir}/raw_{unique_id}.mp4"
        gif_mp4_path = f"{output_dir}/custom_gif_{unique_id}.mp4"

        try:
            ydl_opts = {
                'outtmpl': raw_video,
                'format': 'worstvideo[ext=mp4]/worst[ext=mp4]/worst',
                'quiet': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(saved_url, download=True)
                title = info.get('title', 'GIF Animation')
                if not os.path.exists(raw_video):
                    raw_video = ydl.prepare_filename(info)

            if convert_to_gif_mp4(raw_video, gif_mp4_path, start_sec=start_sec, duration=duration):
                with open(gif_mp4_path, "rb") as gf:
                    await context.bot.send_animation(
                        chat_id=user_id,
                        animation=gf,
                        caption=f"🎞️ {title[:45]}\n⏱️ Range: {start_sec}s - {end_sec}s\n⚡ Ultra Social Bot"
                    )
                await status_msg.delete()
            else:
                await status_msg.edit_text("❌ GIF তৈরি করা সম্ভব হয়নি।")
        except Exception as e:
            await status_msg.edit_text(f"GIF Error: {str(e)[:100]}")
        finally:
            for f in [raw_video, gif_mp4_path]:
                if os.path.exists(f): os.remove(f)
        return

    if user_id in user_waiting_custom_time:
        saved_url = user_waiting_custom_time.pop(user_id)
        try:
            sec = parse_time_str(text)
        except Exception:
            sec = 5

        status_msg = await update.message.reply_text(get_text(user_id, "processing", quality=f"Frame {sec}s"))
        unique_id = str(uuid.uuid4())[:6]
        output_img = f"{output_dir}/custom_frame_{unique_id}.jpg"

        video_stream_url = None
        if "tiktok.com" in saved_url:
            tk = get_tiktok_details(saved_url)
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
                    caption=get_text(user_id, "custom_success", sec=sec) + "\n⚡ Ultra Social Bot"
                )
            await status_msg.delete()
            if os.path.exists(output_img): os.remove(output_img)
        else:
            await status_msg.edit_text(get_text(user_id, "error_frame"))
        return

    if not text.startswith("http://") and not text.startswith("https://"):
        if any(w in lower_text for w in ["language", "ভাষা", "bhasha", "change", "পরিবর্তন", "change language"]):
            await update.message.reply_text(get_text(user_id, "help_lang_resp"), reply_markup=build_language_keyboard())
            return
        if any(w in lower_text for w in ["50mb", "50 mb", "size", "সাইজ", "বড় ফাইল", "limit"]):
            await update.message.reply_text(get_text(user_id, "help_size_resp"))
            return
        if any(w in lower_text for w in ["problem", "error", "সমস্যা", "কাজ করে না", "fail", "not working"]):
            await update.message.reply_text(get_text(user_id, "help_error_resp"))
            return
        if any(w in lower_text for w in ["help", "নির্দেশনা", "নিয়ম", "faq", "কীভাবে", "কিভাবে"]):
            await update.message.reply_text(get_text(user_id, "help_text"))
            return

        await update.message.reply_text("💡 সোশ্যাল মিডিয়ার যেকোনো ভিডিও বা ছবির লিঙ্ক পাঠান অথবা সাহায্য পেতে /help লিখুন।")
        return

    url = text
    if "youtube.com" in url or "youtu.be" in url:
        await update.message.reply_text(get_text(user_id, "error_youtube"))
        return

    user_urls[user_id] = url

    if user_quick_mode.get(user_id, False):
        status_msg = await update.message.reply_text("⚡ কুইক মোড সক্রিয়: 720p ভিডিও প্রস্তুত হচ্ছে...")
        unique_id = str(uuid.uuid4())[:6]
        file_path = f"{output_dir}/quick_{unique_id}.mp4"
        try:
            ydl_opts = {
                'outtmpl': file_path,
                'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
                'merge_output_format': 'mp4',
                'quiet': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Video')
                uploader = info.get('uploader', 'Creator')
                duration = info.get('duration', 0)

            if os.path.exists(file_path):
                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                was_compressed = False

                if size_mb > 50:
                    await status_msg.edit_text(get_text(user_id, "compressing"))
                    compressed_path = f"{output_dir}/quick_comp_{unique_id}.mp4"
                    if compress_video_under_50mb(file_path, compressed_path, duration):
                        os.remove(file_path)
                        file_path = compressed_path
                        size_mb = os.path.getsize(file_path) / (1024 * 1024)
                        was_compressed = True

                if size_mb <= 50:
                    with open(file_path, "rb") as f:
                        await update.message.reply_video(
                            video=f,
                            supports_streaming=True,
                            caption=format_caption(title, uploader, "Fast Mode", "720p Quick", size_mb, was_compressed)
                        )
                    await status_msg.delete()
                    if os.path.exists(file_path): os.remove(file_path)
                    return
        except Exception:
            pass

    has_multi = "instagram.com" in url
    await update.message.reply_text(get_text(user_id, "choose_main"), reply_markup=get_main_menu(user_id, has_multi))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    if data.startswith("setlang_"):
        lang_code = data.split("_")[1]
        user_languages[user_id] = lang_code
        await query.edit_message_text(get_text(user_id, "guide"))
        return

    if data == "cat_cancel":
        user_urls.pop(user_id, None)
        await query.edit_message_text("❌ অপারেশন বাতিল করা হয়েছে। নতুন লিঙ্ক পাঠান।")
        return

    if data == "cat_main":
        url = user_urls.get(user_id, "")
        await query.edit_message_text(get_text(user_id, "choose_main"), reply_markup=get_main_menu(user_id, "instagram.com" in url))
        return
    if data == "cat_video":
        await query.edit_message_text(get_text(user_id, "choose_video"), reply_markup=get_video_menu(user_id))
        return
    if data == "cat_custom_res":
        await query.edit_message_text(get_text(user_id, "choose_custom_res"), reply_markup=get_custom_res_menu(user_id))
        return
    if data == "cat_audio":
        await query.edit_message_text(get_text(user_id, "choose_audio"), reply_markup=get_audio_menu(user_id))
        return
    if data == "cat_gif_tools":
        await query.edit_message_text(get_text(user_id, "choose_gif_tools"), reply_markup=get_gif_tools_menu(user_id))
        return
    if data == "cat_speed":
        await query.edit_message_text(get_text(user_id, "choose_speed"), reply_markup=get_speed_menu(user_id))
        return
    if data == "cat_thumb":
        url = user_urls.get(user_id, "")
        has_photos = False
        if "tiktok.com" in url:
            tk_data = get_tiktok_details(url)
            if tk_data and tk_data.get("images"):
                has_photos = True
        await query.edit_message_text(get_text(user_id, "choose_thumb"), reply_markup=get_thumb_menu(user_id, has_photos))
        return

    url = user_urls.get(user_id)
    if not url:
        await query.edit_message_text(get_text(user_id, "error_expired"))
        return

    output_dir = "temp_downloads"
    os.makedirs(output_dir, exist_ok=True)
    unique_id = str(uuid.uuid4())[:6]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    if data == "tool_gifauto":
        status_msg = await query.edit_message_text("🎞️ ভিডিও থেকে অটোমেটিক GIF তৈরি হচ্ছে...")
        raw_video = f"{output_dir}/raw_autogif_{unique_id}.mp4"
        gif_mp4_path = f"{output_dir}/autogif_{unique_id}.mp4"
        try:
            ydl_opts = {
                'outtmpl': raw_video,
                'format': 'worstvideo[ext=mp4]/worst[ext=mp4]/worst',
                'quiet': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Auto GIF')
                if not os.path.exists(raw_video):
                    raw_video = ydl.prepare_filename(info)

            if convert_to_gif_mp4(raw_video, gif_mp4_path, start_sec=0, duration=7):
                with open(gif_mp4_path, "rb") as gf:
                    await context.bot.send_animation(
                        chat_id=user_id,
                        animation=gf,
                        caption=f"🎞️ {title[:45]} (Auto GIF)\n⚡ Ultra Social Bot"
                    )
                await status_msg.delete()
            else:
                await status_msg.edit_text("❌ Auto GIF তৈরি সম্ভব হয়নি।")
        except Exception as e:
            await status_msg.edit_text(f"GIF Error: {str(e)[:100]}")
        finally:
            for f in [raw_video, gif_mp4_path]:
                if os.path.exists(f): os.remove(f)
        return

    if data in ["multi_all", "multi_first"]:
        status_msg = await query.edit_message_text("📦 ছবি ও মিডিয়া প্রসেস হচ্ছে, দয়া করে অপেক্ষা করুন...")
        media_group = []
        try:
            extracted_items = extract_instagram_media_robust(url)
            if extracted_items:
                target_items = [extracted_items[0]] if data == "multi_first" else extracted_items[:10]
                for idx, (m_url, m_type) in enumerate(target_items):
                    r = requests.get(m_url, headers=headers, timeout=20)
                    if r.status_code == 200:
                        file_bytes = io.BytesIO(r.content)
                        if m_type == "video":
                            file_bytes.name = f"media_{idx}.mp4"
                            media_group.append(InputMediaVideo(media=file_bytes))
                        else:
                            file_bytes.name = f"media_{idx}.jpg"
                            media_group.append(InputMediaPhoto(media=file_bytes))

                if media_group:
                    await context.bot.send_media_group(chat_id=user_id, media=media_group)
                    await status_msg.delete()
                    return

            await status_msg.edit_text("❌ ইনস্টাগ্রামের এই পোস্টটি সম্পূর্ণ প্রাইভেট অথবা লিংকটি বৈধ নয়।")
        except Exception as e:
            await status_msg.edit_text(f"ফটো ডাউনলোড ত্রুটি: {str(e)[:100]}")
        return

    if data == "all_photos_dl":
        status_msg = await query.edit_message_text("📸 টিকটকের সব ছবি নামানো হচ্ছে...")
        tk_data = get_tiktok_details(url)
        if tk_data and tk_data.get("images"):
            images = tk_data["images"]
            media_group = []
            try:
                for idx, img_url in enumerate(images[:10]):
                    r = requests.get(img_url, headers=headers, timeout=20)
                    if r.status_code == 200:
                        b = io.BytesIO(r.content)
                        b.name = f"slide_{idx}.jpg"
                        media_group.append(InputMediaPhoto(media=b))

                if media_group:
                    await context.bot.send_media_group(chat_id=user_id, media=media_group)

                if tk_data.get("audio_url"):
                    ar = requests.get(tk_data["audio_url"], headers=headers, timeout=20)
                    if ar.status_code == 200:
                        aud_b = io.BytesIO(ar.content)
                        aud_b.name = "audio.mp3"
                        await context.bot.send_audio(
                            chat_id=user_id,
                            audio=aud_b,
                            title=tk_data["title"][:40],
                            performer=tk_data["author"]
                        )

                await status_msg.delete()
            except Exception as e:
                await status_msg.edit_text(f"ফটো ত্রুটি: {str(e)[:100]}")
            return
        else:
            await status_msg.edit_text("❌ এতে কোনো ফটো স্লাইড পাওয়া যায়নি।")
            return

    if data.startswith("spd_"):
        speed_factor = float(data.split("_")[1])
        status_msg = await query.edit_message_text(f"⏩ ভিডিওর গতি {speed_factor}x করা হচ্ছে, অপেক্ষা করুন...")
        raw_vid = f"{output_dir}/raw_speed_{unique_id}.mp4"
        spd_vid = f"{output_dir}/speed_{speed_factor}x_{unique_id}.mp4"

        try:
            ydl_opts = {
                'outtmpl': raw_vid,
                'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
                'merge_output_format': 'mp4',
                'quiet': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Speed Video')
                uploader = info.get('uploader', 'Creator')

            if change_video_speed_ffmpeg(raw_vid, spd_vid, speed=speed_factor):
                size_mb = os.path.getsize(spd_vid) / (1024 * 1024)
                with open(spd_vid, "rb") as f:
                    await context.bot.send_video(
                        chat_id=user_id,
                        video=f,
                        supports_streaming=True,
                        caption=format_caption(title, uploader, "Speed Converted", f"{speed_factor}x Speed", size_mb)
                    )
                await status_msg.delete()
            else:
                await status_msg.edit_text("❌ স্পিড কনভার্ট করা সম্ভব হয়নি।")
        except Exception as e:
            await status_msg.edit_text(f"Speed Error: {str(e)[:100]}")
        finally:
            for f in [raw_vid, spd_vid]:
                if os.path.exists(f): os.remove(f)
        return

    if data == "tool_audiotrim":
        user_waiting_audio_trim[user_id] = url
        await query.edit_message_text(get_text(user_id, "audio_trim_prompt"))
        return

    if data == "tool_gifcustom":
        user_waiting_gif_time[user_id] = url
        await query.edit_message_text(get_text(user_id, "gif_prompt"))
        return

    req_type, quality = data.split("_")

    if req_type == "frame" and quality == "custom":
        user_waiting_custom_time[user_id] = url
        await query.edit_message_text(get_text(user_id, "custom_prompt"))
        return

    if req_type == "frame" and quality == "mid":
        status_msg = await query.edit_message_text(get_text(user_id, "processing", quality="Mid Frame"))
        output_img = f"{output_dir}/mid_frame_{unique_id}.jpg"
        target_stream = None
        duration = 10

        if "tiktok.com" in url:
            tk = get_tiktok_details(url)
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
                    caption=get_text(user_id, "mid_success", sec=mid_point) + "\n⚡ Ultra Social Bot"
                )
            await status_msg.delete()
            if os.path.exists(output_img): os.remove(output_img)
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

    if "tiktok.com" in url and req_type not in ["tool"]:
        tk_data = get_tiktok_details(url)
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
                            caption=format_caption(tk_data['title'], tk_data['author'], "TikTok", quality_display)
                        )
                    await status_msg.delete()
                    return

                if req_type == "vid":
                    target_url = tk_data["video_hd"] if quality in ["2160", "1440", "1080", "720", "highest", "doc"] else tk_data["video_sd"]
                    ext = "mp4"
                else:
                    target_url = tk_data["audio_url"]
                    ext = "mp3"

                file_path = f"{output_dir}/tk_{unique_id}.{ext}"
                with requests.get(target_url, stream=True, headers=headers, timeout=60) as r:
                    r.raise_for_status()
                    with open(file_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024*1024):
                            if chunk: f.write(chunk)

                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                was_compressed = False

                if req_type == "vid" and file_size_mb > 50:
                    await status_msg.edit_text(get_text(user_id, "compressing"))
                    compressed_path = f"{output_dir}/tk_comp_{unique_id}.mp4"
                    if compress_video_under_50mb(file_path, compressed_path, tk_data.get("duration", 0)):
                        os.remove(file_path)
                        file_path = compressed_path
                        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                        was_compressed = True
                    else:
                        await status_msg.edit_text(get_text(user_id, "error_compress"))
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
                                caption=f"🎙️ {tk_data['title'][:50]}\n⚡ Ultra Social Bot"
                            )
                        if os.path.exists(ogg_path): os.remove(ogg_path)
                    await status_msg.delete()
                    return

                with open(file_path, "rb") as f:
                    if req_type == "vid":
                        if quality == "doc":
                            await context.bot.send_document(
                                chat_id=user_id,
                                document=f,
                                caption=format_caption(tk_data['title'], tk_data['author'], "TikTok", quality_display, file_size_mb, was_compressed)
                            )
                        else:
                            await context.bot.send_video(
                                chat_id=user_id,
                                video=f,
                                supports_streaming=True,
                                caption=format_caption(tk_data['title'], tk_data['author'], "TikTok", quality_display, file_size_mb, was_compressed)
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
                if file_path and os.path.exists(file_path): os.remove(file_path)
                if thumb_path and os.path.exists(thumb_path): os.remove(thumb_path)

    output_template = f"{output_dir}/media_{unique_id}.%(ext)s"

    if req_type == "thumb":
        ydl_opts = {
            'skip_download': True,
            'writethumbnail': True,
            'outtmpl': output_template,
            'quiet': True,
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
                        caption=format_caption(video_title, uploader, platform_name, quality_display)
                    )
                await status_msg.delete()
            else:
                await status_msg.edit_text(get_text(user_id, "error_frame"))
        except Exception as e:
            await context.bot.send_message(chat_id=user_id, text=f"Error: {str(e)[:150]}")
        finally:
            if file_path and os.path.exists(file_path): os.remove(file_path)
        return

    if req_type in ["vid"]:
        if quality in ["2160", "highest", "doc"]:
            format_opt = "bestvideo[height<=2160]+bestaudio/best[height<=2160]/best"
        elif quality == "1440":
            format_opt = "bestvideo[height<=1440]+bestaudio/best[height<=1440]/best"
        elif quality == "1080":
            format_opt = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
        elif quality in ["720", "normal"]:
            format_opt = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
        elif quality in ["480"]:
            format_opt = "bestvideo[height<=480]+bestaudio/best[height<=480]/best"
        elif quality in ["360"]:
            format_opt = "bestvideo[height<=360]+bestaudio/best[height<=360]/best"
        elif quality in ["240"]:
            format_opt = "bestvideo[height<=240]+bestaudio/best[height<=240]/best"
        elif quality in ["144", "lowest"]:
            format_opt = "worstvideo[height<=144]+worstaudio/worst"
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
            'format': format_opt,
            'merge_output_format': 'mp4',
        }
    else:
        bitrate = quality if quality in ["320", "192", "128"] else "192"
        ydl_opts = {
            'outtmpl': output_template,
            'quiet': True,
            'format': 'bestaudio/best',
            'writethumbnail': True,
            'postprocessors': [
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': bitrate},
                {'key': 'FFmpegMetadata'},
            ],
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
                if os.path.exists(base_name + ".mp4"): file_path = base_name + ".mp4"
            else:
                if os.path.exists(base_name + ".mp3"): file_path = base_name + ".mp3"

        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        was_compressed = False

        if req_type == "vid" and file_size_mb > 50:
            await status_msg.edit_text(get_text(user_id, "compressing"))
            compressed_video = f"{output_dir}/comp_{unique_id}.mp4"
            if compress_video_under_50mb(file_path, compressed_video, duration):
                os.remove(file_path)
                file_path = compressed_video
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                was_compressed = True
            else:
                await status_msg.edit_text(get_text(user_id, "error_compress"))
                return

        if req_type == "aud" and quality == "voice":
            await status_msg.edit_text(get_text(user_id, "processing", quality="Voice Note"))
            ogg_path = f"{output_dir}/voice_{unique_id}.ogg"
            if convert_to_voice_note(file_path, ogg_path):
                with open(ogg_path, "rb") as vf:
                    await context.bot.send_voice(
                        chat_id=user_id,
                        voice=vf,
                        caption=f"🎙️ {video_title[:50]}\n⚡ Ultra Social Bot"
                    )
                if os.path.exists(ogg_path): os.remove(ogg_path)
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
                        caption=format_caption(video_title, channel_name, platform_name, quality_display, file_size_mb, was_compressed)
                    )
                else:
                    await context.bot.send_video(
                        chat_id=user_id,
                        video=f,
                        supports_streaming=True,
                        caption=format_caption(video_title, channel_name, platform_name, quality_display, file_size_mb, was_compressed)
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
            try: os.remove(file_path)
            except Exception: pass
        if thumb_jpg and os.path.exists(thumb_jpg):
            try: os.remove(thumb_jpg)
            except Exception: pass

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
    app.add_handler(CommandHandler("quick", cmd_quick))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("Ultra 4K/2K Social Media Bot with Guaranteed Photo Fix is Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
