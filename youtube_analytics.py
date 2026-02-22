import requests
import time
import csv
import os
import sys
from datetime import date
from collections import defaultdict
import matplotlib.pyplot as plt

# ======================
# CONFIG (EDIT THESE)
# ======================
API_KEY = "AIzaSyCPqb1atyX1ytVklcCFi3hPgMLLecUUygI"
CHANNEL_ID = "UCgG28RTH48Imf8feEUycW8A"
MAX_RESULTS = 5
BASE_URL = "https://www.googleapis.com/youtube/v3"

# ======================
# PATH SAFETY
# ======================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(BASE_DIR, exist_ok=True)

CSV_FILE = os.path.join(BASE_DIR, "daily_video_stats.csv")
CHART_FILE = os.path.join(BASE_DIR, "engagement_trend.png")
LOG_FILE = os.path.join(BASE_DIR, "run.log")

# ======================
# LOGGING
# ======================
def log(message):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(message + "\n")

# ======================
# SAFETY CHECK
# ======================
def already_logged_today(csv_file, today):
    if not os.path.isfile(csv_file):
        return False

    try:
        with open(csv_file, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)

            if not header or "date" not in header:
                return False

            date_index = header.index("date")

            for row in reader:
                if len(row) > date_index and row[date_index] == today:
                    return True
    except Exception:
        return False

    return False

# ======================
# YOUTUBE API
# ======================
def get_latest_videos(channel_id):
    url = f"{BASE_URL}/search"
    params = {
        "part": "snippet",
        "channelId": channel_id,
        "order": "date",
        "type": "video",
        "maxResults": MAX_RESULTS,
        "key": API_KEY
    }

    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json().get("items", [])

def get_video_stats(video_id):
    url = f"{BASE_URL}/videos"
    params = {
        "part": "statistics",
        "id": video_id,
        "key": API_KEY
    }

    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    items = r.json().get("items", [])
    return items[0]["statistics"] if items else None

# ======================
# MAIN EXECUTION
# ======================
today = date.today().isoformat()
log(f"[START] {today}")

if already_logged_today(CSV_FILE, today):
    log(f"[SKIP] {today} already logged")
    print("[INFO] Data already logged today. Skipping run.")
    sys.exit(0)

try:
    videos = get_latest_videos(CHANNEL_ID)
except Exception as e:
    log(f"[ERROR] Failed to fetch videos: {e}")
    sys.exit(1)

rows_written = False

try:
    file_exists = os.path.isfile(CSV_FILE)

    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow([
                "date",
                "video_id",
                "title",
                "views",
                "likes",
                "engagement_ratio"
            ])

        for item in videos:
            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]

            stats = get_video_stats(video_id)
            time.sleep(0.2)  # rate-limit safety

            if not stats:
                continue

            views = int(stats.get("viewCount", 0))
            likes = int(stats.get("likeCount", 0))
            engagement = round(likes / views, 6) if views > 0 else 0

            writer.writerow([
                today,
                video_id,
                title,
                views,
                likes,
                engagement
            ])

            rows_written = True

except PermissionError:
    log("[WARN] CSV locked (probably open in Excel)")
    sys.exit(0)

if not rows_written:
    log("[WARN] No rows written")
    sys.exit(0)

log(f"[CSV] Logged data for {today}")
print(f"[OK] Logged data for {today}")

# ======================
# CHART GENERATION
# ======================
video_history = defaultdict(list)

try:
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            video_history[row["title"]].append(
                (row["date"], float(row["engagement_ratio"]))
            )

    plt.figure(figsize=(10, 5))

    for title, points in video_history.items():
        dates = [p[0] for p in points]
        ratios = [p[1] for p in points]
        plt.plot(dates, ratios, marker="o", label=title[:30])

    plt.xlabel("Date")
    plt.ylabel("Engagement (Likes / Views)")
    plt.title("Engagement Trend Over Time")

    plt.legend(
        fontsize=8,
        loc="upper left",
        bbox_to_anchor=(1.02, 1),
        frameon=True
    )

    plt.tight_layout()
    plt.savefig(CHART_FILE)
    plt.close()

    log("[CHART] Saved engagement_trend.png")
    print("[OK] Saved engagement_trend.png")

except Exception as e:
    log(f"[WARN] Chart failed: {e}")

log(f"[DONE] {today}\n")
