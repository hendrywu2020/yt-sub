import os
import google.generativeai as genai
from opencc import OpenCC
import yt_dlp
import time

# --- 配置區 ---
# 從環境變數讀取機敏資訊
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
YOUTUBE_CHANNEL_ID = os.getenv('YOUTUBE_CHANNEL_ID')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
CHANNEL_URL = f"https://www.youtube.com/channel/{YOUTUBE_CHANNEL_ID}"

# 設定 Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest') # 使用性價比高的 Flash 模型

# AI 處理指令 (您的需求)
AI_PROMPT = """
你是專業的文字採編，請對接下來提供的文本做以下工作：
A、去除所有時間戳，並根據上下文意思的連貫性和完整性，添加恰當的標點符號，並分成大小段落。確保每個段落的文字數量都少於200字。
B、去除所有口頭禪、語氣詞和重複的詞語（例如 "那麼"、"就是說"、"嗯"、"啊" 等），但對其他有效文字不做任何刪減，保持原文資訊的原汁原味。
C、絕對不要進行任何形式的總結或評論。
D、請直接輸出處理好的、純文字的 Markdown 格式文本。
"""

# OpenCC 用於繁簡轉換
cc = OpenCC('s2twp')

# yt-dlp 選項
ydl_opts = {
    'writesubtitles': True,
    'writeautomaticsub': True,
    'subtitleslangs': ['zh-Hant', 'zh-Hans', 'en'],
    'subtitlesformat': 'srv3',
    'skip_download': True,
    'outtmpl': 'subtitles/%(upload_date)s_%(id)s.%(ext)s',
    'dateafter': 'now-2days',
    'playlistend': 5,
    'ignoreerrors': True,
    'verbose': True,
    'apikey': YOUTUBE_API_KEY,
    'cookiefile': 'cookies.txt',
}

# --- 函數區 ---
def process_with_gemini(text):
    """調用 Gemini API 處理文字"""
    try:
        print("  - Sending text to Gemini API for processing...")
        full_prompt = AI_PROMPT + "\n\n" + text
        response = model.generate_content(full_prompt)
        print("  - Received response from Gemini.")
        return response.text
    except Exception as e:
        print(f"  - An error occurred with Gemini API: {e}")
        return None

# --- 主流程 ---
# 1. 下載字幕
print("Step 1: Fetching subtitles...")
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([CHANNEL_URL])
print("Subtitle fetching process finished.\n")

# 2. 處理下載的文件
print("Step 2: Processing downloaded files...")
SUBTITLES_DIR = 'subtitles'
PROCESSED_DIR = 'processed_articles' # 建立一個新目錄存放處理好的文章

if not os.path.exists(PROCESSED_DIR):
    os.makedirs(PROCESSED_DIR)

if not os.path.exists(SUBTITLES_DIR) or not os.listdir(SUBTITLES_DIR):
    print("No new subtitles were downloaded. Exiting.")
else:
    for filename in os.listdir(SUBTITLES_DIR):
        if filename.endswith(".srv3"):
            print(f"- Processing file: {filename}")
            filepath = os.path.join(SUBTITLES_DIR, filename)

            # 讀取並先做繁簡轉換
            with open(filepath, 'r', encoding='utf-8') as f:
                original_text = f.read()
            converted_text = cc.convert(original_text)

            # 調用 AI 進行清洗
            processed_content = process_with_gemini(converted_text)

            if processed_content:
                # 建立新的 .md 文件名
                new_filename = os.path.splitext(os.path.splitext(filename)[0])[0] + '.md'
                new_filepath = os.path.join(PROCESSED_DIR, new_filename)

                # 將 AI 處理完的內容寫入 .md 文件
                with open(new_filepath, 'w', encoding='utf-8') as f:
                    f.write(processed_content)
                print(f"  - Successfully created processed article: {new_filepath}\n")
            else:
                print(f"  - Failed to process {filename} with AI. Skipping.\n")
            
            # 為了避免達到 Gemini 的請求頻率限制，可以加入短暫延遲
            time.sleep(2) # 延遲 2 秒

print("All tasks completed.")
