from io import BytesIO

import pandas as pd
import requests
from logging import getLogger

from database.storage import upload_file, file_exists
from messaging.utils import get_pdf_title_from_meal_name

log = getLogger("PDF Downloader")


def save_all_pdfs(recipes: pd.DataFrame):
    counter = 0
    for idx, row in recipes.iterrows():
        counter_str = f"[{idx + 1}/{len(recipes)}]"
        pdf_title = get_pdf_title_from_meal_name(row["title"])
        try:
            save_single_pdf(url=row["pdf_link"], db_ref=pdf_v2_ref(pdf_title))
            log.debug(f"{counter_str} Downloaded {row['pdf_link']}")
            counter += 1
        except Exception as e:
            log.warning(f"{counter_str} Error in downloading pdf: {e}")
    log.info(f"Downloaded {counter} PDFs")


def save_single_pdf(url: str, db_ref: str) -> None:
    response = requests.get(url)
    assert response.status_code == 200, f"Error in downloading pdf: {response.status_code}"
    assert response.headers["Content-Type"] == "application/pdf", f"Error in pdf: {response.headers['Content-Type']}"
    assert len(response.content) > 1000, "Error in downloading pdf: File is empty"
    buffer = BytesIO()
    buffer.write(response.content)
    buffer.seek(0)
    upload_file(buffer, ref=db_ref)


def pdf_v2_ref(pdf_title: str):
    return f"pdf_v2/{pdf_title}.pdf"


def remove_recipes_with_faulty_pdfs(recipes: pd.DataFrame) -> pd.DataFrame:
    counter = 0
    for idx, row in recipes.iterrows():
        pdf_title = get_pdf_title_from_meal_name(row["title"])
        ref = pdf_v2_ref(pdf_title)
        if not file_exists(ref=ref):
            print(f"PDF not found: {ref}")
            counter += 1
            recipes.drop(idx, inplace=True)
    return recipes
