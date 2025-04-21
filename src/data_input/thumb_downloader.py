import pandas as pd
from PIL import Image
import requests
import numpy as np
import os
from threading import Thread

from utils.config import ROOT_DIR
from utils.logger import create_logger


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
        print(f"Error retrieving image for {title}: {e}")
        return None


def save_single_image(row, index):
    image = get_image(image_url=row['hero_image'], title=row['title'])
    save_path = f'{output_path}/{row["title"]}.jpg'
    image.save(save_path, quality=25)
    log.debug(f"[{index}] Saved image for {row['title']} to {save_path}")


def save_images(df: pd.DataFrame):
    for index, row in df.iterrows():
        save_single_image(row, index)


def save_images_threaded(df: pd.DataFrame, num_threads: int = 20):
    df_split = np.array_split(df, num_threads)
    threads = []

    for idx, df_part in enumerate(df_split):
        thread = Thread(target=save_images, kwargs={'df': df_part})
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    log.info("All images downloaded and saved.")


if __name__ == "__main__":
    log = create_logger("Image Downloader")
    input_path = f'{ROOT_DIR}/data/temp_data/cleaned.csv'
    output_path = f'{ROOT_DIR}/data/temp_thumbs'
    os.makedirs(output_path, exist_ok=True)
    df = pd.read_csv(input_path)
    df = df[['title', 'hero_image']]
    save_images_threaded(df)