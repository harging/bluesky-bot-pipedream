import io
import os
import re
from datetime import date

import requests
import pandas as pd
from bsky_bridge import BskySession
from bsky_bridge import post_image

data_url = "google_spreadsheet_url_ending_csv"

# column names, matched exactly as they appear in the sheet header
COL_FILM = "Film"
COL_CINEMA = "Cinema"
COL_DATE = "Date"
COL_TIME = "Time"
COL_SCREEN = "Screen"
COL_SEAT = "Seat"
COL_PRICE = "Price"
COL_ISSUED_BY = "Issued by"
COL_EIFF = "EIFF"
COL_ALT_TEXT = "Alt text"
COL_IMAGE = "Image"

# order controls the order fields appear in the post text
CAPTION_COLUMNS = [COL_FILM, COL_CINEMA, COL_DATE, COL_TIME, COL_SCREEN, COL_SEAT, COL_PRICE,
                   COL_ISSUED_BY, COL_EIFF]

DRIVE_ID_RE = re.compile(r"/d/([\w-]+)|[?&]id=([\w-]+)")


def drive_share_link_to_direct_url(share_link):
    # handles both /file/d/<id>/view and ...?id=<id> style Drive links
    match = DRIVE_ID_RE.search(share_link)
    if not match:
        raise ValueError(f"Couldn't find a Drive file ID in: {share_link}")
    file_id = match.group(1) or match.group(2)
    return "http://drive.google.com/uc?export=view&id=" + file_id


def build_caption(row):
    parts = []
    for col in CAPTION_COLUMNS:
        value = row.get(col)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    return " — ".join(parts)


def is_usable_row(item):
    for col in (COL_IMAGE, COL_ALT_TEXT, COL_DATE):
        if not (col in item and isinstance(item[col], str) and item[col].strip()):
            return False
    return True


def matches_today(item, today):
    try:
        ticket_date = pd.to_datetime(item[COL_DATE], format="%Y-%m-%d").date()
    except (ValueError, TypeError):
        return False  # skip rows with a date we can't parse
    return ticket_date.month == today.month and ticket_date.day == today.day


def handler(pdm: "pipedream"):
    bsky_session = BskySession(os.environ.get("BSKY_USER"), os.environ.get("BSKY_PASS"))

    csv = requests.get(data_url, timeout=30).content
    df = pd.read_csv(io.StringIO(csv.decode('utf-8')))

    today = date.today()
    matches = [item for item in df.to_dict(orient='records')
               if is_usable_row(item) and matches_today(item, today)]

    if not matches:
        return {"posted": 0, "message": "No tickets match today's date."}

    posted, errors = [], []
    for i, item in enumerate(matches):
        film = item.get(COL_FILM, f"row {i}")
        try:
            image_url = drive_share_link_to_direct_url(item[COL_IMAGE])
            image_bytes = requests.get(image_url, timeout=30).content
            filename = f"/tmp/image_{i}.png"
            with open(filename, "wb") as f:
                f.write(image_bytes)

            post_image(bsky_session, build_caption(item), filename, item[COL_ALT_TEXT])
            posted.append(film)
        except Exception as e:
            # one bad ticket (dead link, network blip) shouldn't stop the rest
            errors.append({"film": film, "error": str(e)})

    return {"posted": len(posted), "films": posted, "errors": errors}
