from playwright.sync_api import sync_playwright
import requests
import pandas as pd
import datetime as dt
import os
import re
from bs4 import BeautifulSoup

os.makedirs("data", exist_ok=True)

all_apps_ids = [
    "6502288185",
    "1060048474",
    "1387380275",
    "1496540793",
    "1225362709",
    "1467891225",
    "1630681705",
    "510164019",
    "1403342029",
    "942919872",
    "1179371472",
    "1610129795",
    "6499590549",
    "1210668838",
    "1579229899"
]

country = "jo"
results = []

# ---------------------------
# 1. START PLAYWRIGHT ONCE
# ---------------------------
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()

    def block(route):
        if route.request.resource_type in ["image", "font", "media", "stylesheet"]:
            route.abort()
        else:
            route.continue_()

    context.route("**/*", block)
    page = context.new_page()

    # ---------------------------
    # 2. LOOP APPS
    # ---------------------------
    for app_id in all_apps_ids:

        print(f"Processing {app_id}")

        # ---------------------------
        # A) iTunes metadata
        # ---------------------------
        url = f"https://itunes.apple.com/lookup?id={app_id}&country={country}"
        data = requests.get(url).json()

        if not data["results"]:
            continue

        app = data["results"][0]
        total_ratings = app.get("userRatingCount", 0)

        # ---------------------------
        # B) Apple Store histogram
        # ---------------------------
        app_url = f"https://apps.apple.com/jo/app/id{app_id}"

        page.goto(app_url, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)

        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        histogram = {}

        rows = soup.select("[data-testid^='star-row-']")

        for row in rows:
            testid = row.get("data-testid", "")
            star = testid.split("-")[-1]

            match = re.search(r"width:\s*([0-9.]+)%", str(row))
            if match:
                histogram[star] = float(match.group(1))

        # ensure all stars exist
        for s in ["1", "2", "3", "4", "5"]:
            histogram.setdefault(s, 0.0)

        # ---------------------------
        # C) convert % → counts
        # ---------------------------
        star_counts = {
            f"{s}_star_count": round(total_ratings * histogram[s] / 100)
            for s in ["1", "2", "3", "4", "5"]
        }

        # ---------------------------
        # D) save row
        # ---------------------------
        results.append({
            "Store": "App Store",
            "Snapshot_Date": dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "app_id": app.get("bundleId"),
            "title": app.get("trackName"),
            "summary": app.get("trackCensoredName"),
            "rev_score": app.get("averageUserRating"),
            "num_of_ratings": total_ratings,
            "num_of_interactions": 0,
            "installs": 0,
            "realInstalls": 0,
            "version": app.get("version"),
            "released": pd.to_datetime(app.get("releaseDate")).strftime("%B %d, %Y"),
            "lastUpdatedOn": pd.to_datetime(app.get("currentVersionReleaseDate")).strftime("%B %d, %Y"),

            **star_counts
        })

    browser.close()

# ---------------------------
# 3. SAVE DATAFRAME
# ---------------------------
df = pd.DataFrame(results)

file_path = "data/Jordan_banks_Reviews_AppleStore.xlsx"
df.to_excel(file_path, index=False)

print("Saved:", file_path)
print("Files in data folder:", os.listdir("data"))
