import os
import google.generativeai as genai
from opencc import OpenCC
import yt_dlp
import time
from datetime import datetime, timezone, timedelta

# --- 配置區 ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
YOUTUBE_CHANNEL_ID = os.getenv('YOUTUBE_CHANNEL_ID')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
CHANNEL_URL = f"https://www.youtube.com/channel/{YOUTUBE_CHANNEL_ID}"
PROCESSED_DIR = 'processed_articles'

# 設定時區為上海/台北 (UTC+8)
TZ_SHANGHAI = timezone(timedelta(hours=8))

# --- 初始化工具 ---
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')
cc = OpenCC('s2twp')

# --- AI 指令 ---
AI_PROMPT = """
你是專業的文字採編，請對接下來提供的文本做以下工作：
A、去除所有時間戳，並根據上下文意思的連貫性和完整性，添加恰當的標點符號，並分成大小段落。確保每個段落的文字數量都少於200字。
B、去除所有口頭禪、語氣詞和重複的詞語（例如 "那麼"、"就是說"、"嗯"、"啊" 等），但對其他有效文字不做任何刪減，保持原文資訊的原汁原味。
C、絕對不要進行任何形式的總結或評論。
D、請直接輸出處理好的、純文字的 Markdown 格式文本。
"""

# --- 函數區 ---
def process_with_gemini(text):
    try:
        print("    - Sending text to Gemini API for processing...")
        full_prompt = AI_PROMPT + "\n\n" + text
        response = model.generate_content(full_prompt)
        print("    - Received response from Gemini.")
        cleaned_text = response.text.strip().replace('```markdown', '').replace('```', '')
        return cleaned_text
    except Exception as e:
        print(f"    - An error occurred with Gemini API: {e}")
        return None

# --- 主流程 ---
print("Step 1: Preparing to fetch video list...")
if not os.path.exists(PROCESSED_DIR):
    os.makedirs(PROCESSED_DIR)

# 獲取影片列表，只取最新的那一個來處理
ydl_info_opts = {
    'playlistend': 1, # **只獲取播放列表中的第1個（最新的）影片**
    'dateafter': 'now-1day', # 時間範圍設為1天內
    'ignoreerrors': True,
    'extract_flat': 'in_playlist',
    'apikey': YOUTUBE_API_KEY,
    'cookiefile': 'cookies.txt',
}

with yt_dlp.YoutubeDL(ydl_info_opts) as ydl:
    playlist_info = ydl.extract_info(CHANNEL_URL, download=False)

if not playlist_info or not playlist_info.get('entries'):
    print("No new videos found within the time window. Exiting.")
    exit()

# **我們只處理列表中的第一個（也就是最新的）影片**
video_entry = playlist_info['entries'][0]
video_id = video_entry['id']
# 獲取影片原始標題，並移除可能干擾 Markdown 格式的特殊符號
video_title = video_entry.get('title', '每日新聞').replace('"', "'").replace('#', '')
video_url = video_entry['url']

print(f"Step 2: Found latest video to process: '{video_title}'")

# 下載字幕
print("  - Downloading subtitles...")
subtitle_path_template = os.path.join('temp_subtitles', f'{video_id}.%(ext)s')
if not os.path.exists('temp_subtitles'):
    os.makedirs('temp_subtitles')
    
ydl_sub_opts = {
    'writesubtitles': True, 'writeautomaticsub': True,
    'subtitleslangs': ['zh-Hant', 'zh-Hans', 'en'],
    'subtitlesformat': 'srv3', 'skip_download': True,
    'outtmpl': subtitle_path_template, 'cookiefile': 'cookies.txt',
}

subtitle_filename = ""
with yt_dlp.YoutubeDL(ydl_sub_opts) as sub_ydl:
    sub_ydl.download([video_url])
    for lang in ['zh-Hant', 'zh-Hans', 'en']:
        expected_path = os.path.join('temp_subtitles', f'{video_id}.{lang}.srv3')
        if os.path.exists(expected_path):
            subtitle_filename = expected_path
            break

if not subtitle_filename:
    print("  - No subtitles found. Exiting.")
    exit()

# 讀取、轉換、並用 AI 清洗
print("Step 3: Processing text with AI...")
with open(subtitle_filename, 'r', encoding='utf-8') as f:
    original_text = f.read()

converted_text = cc.convert(original_text)
processed_content = process_with_gemini(converted_text)

if processed_content:
    print("Step 4: Generating final Hugo article file...")
    # --- 按照您的格式生成檔名和文件頭 ---
    today = datetime.now(TZ_SHANGHAI)
    filename_date = today.strftime("%Y%m%d")
    
    # 建立完全符合您博客格式的檔名
    final_filename = os.path.join(PROCESSED_DIR, f"{filename_date}-ltnews.md")
    
    # 文件頭：標題日期
    title_date = today.strftime("%Y%m%d")
    # 文件頭：文章日期
    post_date = today.isoformat()

    # 組合文件頭
    front_matter = f"""---
title: "{title_date} LT新聞轉錄"
date: "{post_date}"
draft: false
author: "LT視界"
---
"""
    # 組合最終內容
    final_content = (
        front_matter +
        "\n# 今日重要新聞分享\n\n" +
        f"## {video_title}\n\n" +
        processed_content
    )
    
    with open(final_filename, 'w', encoding='utf-8') as f:
        f.write(final_content)
    print(f"  - Successfully created Hugo article: {final_filename}")
else:
    print("  - Failed to process with AI. No article was generated.")

print("\nAll tasks completed.")
