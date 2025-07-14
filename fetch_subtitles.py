import os
import yt_dlp
from opencc import OpenCC

# 從環境變數中讀取 YouTube 頻道 ID 和 API Key
# 這是 GitHub Actions 的標準做法，更安全
CHANNEL_ID = os.getenv('YOUTUBE_CHANNEL_ID')
API_KEY = os.getenv('YOUTUBE_API_KEY')
CHANNEL_URL = f"https://www.youtube.com/channel/{CHANNEL_ID}"

# 建立一個 OpenCC 實例，用於's2twp' (簡體到繁體台灣用語)
cc = OpenCC('s2twp')

# 設定 yt-dlp 選項
ydl_opts = {
    'writesubtitles': True,      # 啟用字幕下載
    'writeautomaticsub': True,   # 如果沒有手動字幕，也下載自動字幕
    'subtitleslangs': ['zh-Hant', 'zh-Hans', 'en'], # 優先下載繁中、簡中、英文
    'subtitlesformat': 'srv3',   # 字幕格式 (純文字)
    'skip_download': True,       # **極其重要：跳過影片下載，只處理字幕**
    'outtmpl': 'subtitles/%(upload_date)s_%(id)s.%(ext)s', # 輸出路徑和檔名格式
    'dateafter': 'now-2days',    # **只處理過去2天的影片，避免重複下載**
    'playlistend': 5,            # 為防止頻道一天發太多影片，最多檢查最新的5個
    'ignoreerrors': True,        # 遇到錯誤時繼續
    'verbose': True,             # 輸出詳細日誌，方便在 GitHub Actions 中除錯
    'apikey': API_KEY,           # 使用您的 API Key
}

# 執行下載
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    print(f"Fetching subtitles for channel: {CHANNEL_URL}")
    ydl.download([CHANNEL_URL])
    print("Subtitle fetching process finished.")

# 遍歷下載的字幕文件並進行繁簡轉換
output_dir = 'subtitles'
if not os.path.exists(output_dir):
    print(f"Directory '{output_dir}' not found. No subtitles were downloaded.")
else:
    for filename in os.listdir(output_dir):
        if filename.endswith(".srv3"):
            filepath = os.path.join(output_dir, filename)
            try:
                with open(filepath, 'r+', encoding='utf-8') as f:
                    original_text = f.read()
                    converted_text = cc.convert(original_text)
                    f.seek(0)
                    f.write(converted_text)
                    f.truncate()
                print(f"Converted {filename} to Traditional Chinese.")
            except Exception as e:
                print(f"Could not process file {filename}: {e}")
