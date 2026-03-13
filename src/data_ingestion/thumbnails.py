from io import BytesIO

import pandas as pd
from PIL import Image
import requests
import numpy as np
from threading import Thread
from logging import getLogger

from data_ingestion import CLEANED_RECIPES_TABLE
from database.engine import engine
from database.storage import upload_file

log = getLogger("Image Downloader")


def crop_to_square(img: Image.Image) -> Image.Image:
    width, height = img.size
    min_dim = min(width, height)
    left = (width - min_dim) // 2
    top = (height - min_dim) // 2
    right = left + min_dim
    bottom = top + min_dim
    return img.crop((left, top, right, bottom))


def get_image(image_url: str, title: str) -> Image.Image | None:
    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()
        image = Image.open(response.raw)
        image = crop_to_square(image)
        image = image.resize((320, 320))
        return image
    except Exception as e:
        log.error(f"Error retrieving image for {title}: {e}")
        return None


def save_single_image(image_url, title):
    image = get_image(image_url=image_url, title=title)
    buffer = BytesIO()
    image.save(buffer, "JPEG", quality=25)
    buffer.seek(0)
    upload_file(buffer, reference=f"thumbnails/{title}")


def save_images(df: pd.DataFrame):
    for index, row in df.iterrows():
        save_single_image(image_url=row["hero_image"], title=row["title"])
        log.debug(f"[{index}] Saved image for {row["title"]}")


def save_images_threaded(df: pd.DataFrame, num_threads: int = 20):
    df_split = np.array_split(df, num_threads)
    threads = []
    for idx, df_part in enumerate(df_split):
        thread = Thread(target=save_images, kwargs={"df": df_part})
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()
    log.info("All images downloaded and saved.")


if __name__ == "__main__":
    cleaned_recipes = pd.read_sql_table(CLEANED_RECIPES_TABLE, con=engine)
    cleaned_recipes = cleaned_recipes[["title", "hero_image"]]
    save_images_threaded(cleaned_recipes)
