import io
import os
import random
import requests
import urllib.request
import pandas as pd
from PIL import Image
from bsky_bridge import BskySession
from bsky_bridge import post_image

data_url = "google_spreadsheet_url_ending_csv"
filename = "/tmp/image.png"


def handler(pdm: "pipedream"):
    bsky_session = BskySession(os.environ.get("BSKY_USER"), os.environ.get("BSKY_PASS"))

    csv = requests.get(data_url).content
    df = pd.read_csv(io.StringIO(csv.decode('utf-8')))
    data = df.to_dict(orient='records')

    data = [item for item in data
            if ("image_url" in item and type(item["image_url"]) == str and item["image_url"])
            and ("alt_text" in item and type(item["alt_text"]) == str and item["alt_text"])
            ]

    item = random.choice(data)
    image_id = item["image_url"].split("/")[5]
    image_url = "http://drive.google.com/uc?export=view&id=" + image_id
    alt_text = item["alt_text"]
    text = ""

    urllib.request.urlretrieve(image_url, filename)

    post_image(bsky_session, text, filename, alt_text)
