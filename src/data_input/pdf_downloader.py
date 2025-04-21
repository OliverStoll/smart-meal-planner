import os

import fitz
import pandas as pd
import requests
from utils.logger import create_logger

from src.meals import HfMealManager


class PdfManager:
    log = create_logger("PDF Manager")
    csv_data_path = 'data/cleaned_data_v2.csv'

    def __init__(self, recipes: pd.DataFrame, output_path: str = 'data/pdfs_v2'):
        self.recipes = recipes
        self.output_path = output_path
        os.makedirs(self.output_path, exist_ok=True)

    def download_all_pdfs(self):
        df = pd.read_csv(self.csv_data_path)
        os.makedirs(self.output_path, exist_ok=True)
        counter = 0
        for idx, row in df.iterrows():
            counter_str = f"[{idx+1}/{len(df)}]"
            pdf_title = self.get_pdf_title(row['title'])
            try:
                self.download_single_pdf(row['pdf_link'], f"{self.output_path}/{pdf_title}.pdf")
                self.log.debug(f"{counter_str} Downloaded {row['pdf_link']}")
                counter += 1
            except Exception as e:
                self.log.warning(f"{counter_str} Error in downloading pdf: {e}")
        self.log.info(f"Downloaded {counter} PDFs")

    def download_single_pdf(self, pdf_url: str, save_path: str) -> None:
        response = requests.get(pdf_url)
        assert response.status_code == 200, f"Error in downloading pdf: {response.status_code}"
        assert response.headers['Content-Type'] == 'application/pdf', f"Error in downloading pdf: {response.headers['Content-Type']}"
        assert len(response.content) > 1000, f"Error in downloading pdf: File is empty"
        with open(save_path, 'wb') as f:
            f.write(response.content)

    def remove_faulty_pdfs(self):
        df = pd.read_csv(self.csv_data_path)
        counter = 0
        for idx, row in df.iterrows():
            pdf_title = row['title'].replace(' ', '_').replace(':', '').replace('!', '').replace('&', 'und')
            pdf_path = f"{self.output_path}/{pdf_title}.pdf"
            if not os.path.exists(pdf_path):
                print(f"PDF not found: {pdf_path}")
                counter += 1
                df.drop(idx, inplace=True)
            if not self._check_pdf_page_count(pdf_path):
                print(f"PDF has wrong page count: {pdf_path}")
                os.remove(pdf_path)
                counter += 1
                df.drop(idx, inplace=True)
        df.to_csv(self.csv_data_path, index=False)
        print(f"Removed {counter} PDFs")

    def _check_pdf_page_count(self, pdf_path: str, expected_pages: int = 2):
        with fitz.open(pdf_path) as pdf_document:
            page_count = pdf_document.page_count

        self.log.info(f"Page Count: {page_count}")
        return page_count == expected_pages

    @staticmethod
    def get_pdf_title(title: str) -> str:
        return HfMealManager().get_pdf_title_from_meal_name(title)
