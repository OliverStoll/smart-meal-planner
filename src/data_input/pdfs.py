import io
import requests
import pandas as pd
import os
import json
import re
import ast
from time import sleep
import fitz  # PyMuPDF
from PIL import Image
from utils.logger import create_logger

from meals import HfMealManager

EXAMPLE_PATH = '/data/pdfs_v2/Alpine_Käsespätzlepfanne_mit_Birne_und_Bacon.pdf'


class PDF_Manager:
    log = create_logger("PDF Manager")
    csv_data_path = 'data/cleaned_data_v2.csv'
    pdfs_path = 'data/pdfs_v2'

    def _check_pdf_page_count(self, pdf_path, expected_pages=2):
        pdf_document = fitz.open(pdf_path)
        page_count = pdf_document.page_count
        print(f"Page Count: {page_count}")
        pdf_document.close()
        return page_count == expected_pages

    def remove_faulty_pdfs(self):
        df = pd.read_csv(self.csv_data_path)
        counter = 0
        for idx, row in df.iterrows():
            pdf_title = row['title'].replace(' ', '_').replace(':', '').replace('!', '').replace('&', 'und')
            pdf_path = f"{self.pdfs_path}/{pdf_title}.pdf"
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

    def download_single_pdf(self, url, save_path):
        response = requests.get(url)
        assert response.status_code == 200, f"Error in downloading pdf: {response.status_code}"
        assert response.headers['Content-Type'] == 'application/pdf', f"Error in downloading pdf: {response.headers['Content-Type']}"
        assert len(response.content) > 1000, f"Error in downloading pdf: File is empty"
        with open(save_path, 'wb') as f:
            f.write(response.content)

    def get_pdf_title(self, title):
        return HfMealManager().get_pdf_title_from_meal_name(title)

    def download_all_pdfs(self):
        df = pd.read_csv(self.csv_data_path)
        os.makedirs(self.pdfs_path, exist_ok=True)
        counter = 0
        for idx, row in df.iterrows():
            counter_str = f"[{idx+1}/{len(df)}]"
            pdf_title = self.get_pdf_title(row['title'])
            try:
                self.download_single_pdf(row['pdf_link'], f"{self.pdfs_path}/{pdf_title}.pdf")
                self.log.debug(f"{counter_str} Downloaded {row['pdf_link']}")
                counter += 1
            except Exception as e:
                self.log.warning(f"{counter_str} Error in downloading pdf: {e}")
        self.log.info(f"Downloaded {counter} PDFs")


class PDF_Creator:
    log = create_logger("PDF Creator")
    old_save_dir = "data/pdfs_v2"
    save_dir = "data/pdfs_v2_mobile"
    text_l_padding = 175
    l_padding = 5
    r_padding = 5
    t_padding = 30
    img_txt_spacing = 10
    width = 600
    height = 9999
    step_height = 150
    fontsize = 26
    paragraph_spacing = fontsize * 1.0
    instruction_step_spacing = 35
    line_height = 1.20
    fontname = "helv"
    instruction_img_crop = (0.26, 0.26, 0.17, 0.18)

    def __init__(self):
        os.makedirs(self.save_dir, exist_ok=True)

    @staticmethod
    def crop_image_percentages(img, left, right, top, bottom):
        """Crops an image with given percentages of the image size from each side"""
        width, height = img.size
        left = int(left * width)
        top = int(top * height)
        right = width - int(right * width)
        bottom = height - int(bottom * height)
        return img.crop((left, top, right, bottom))

    def get_center_crop_first_page_img(self, title, path='data/pdfs_v2'):
        pdf = fitz.open(f"{path}/{title}.pdf")
        page_1 = pdf.load_page(0)
        pix = page_1.get_pixmap()
        img = Image.open(io.BytesIO(pix.tobytes()))
        cropped_img = self.crop_image_percentages(img, 0.15, 0.35, 0.24, 0.053)
        return cropped_img

    def _get_instruction_images(self, recipe_entry: pd.Series):
        all_image_links = ast.literal_eval(recipe_entry["instruction_images"])
        all_images = []
        for idx, image_url in enumerate(all_image_links):
            image = Image.open(io.BytesIO(requests.get(image_url).content))
            image = self.crop_image_percentages(image, *self.instruction_img_crop)
            try:
                img_buffer = io.BytesIO()
                image.save(img_buffer, format="JPEG", quality=100)
                img_buffer.seek(0)
            except Exception as e:
                self.log.error(f"Error in converting image: {e}")
                img_buffer = io.BytesIO()
                image.save(img_buffer, format="PNG")
                img_buffer.seek(0)
            all_images.append(img_buffer)
        return all_images

    def _get_instructions(self, recipe_entry: pd.Series, num_meals: int):
        """ Replaces all placeholders in the instructions with the correct values (with and without unit) """
        all_instructions = ast.literal_eval(recipe_entry["instructions"])
        placeholder_patterns = [r'\[(\d+)\s*(\w+)\]', r'\[(\d+)\s*\w*\]']
        factor = num_meals / 2

        def multiply_match(match, factor):
            amount = int(match.group(1))
            unit = ' ' + match.group(2) if len(match.groups()) > 1 else ''
            new_amount = amount * factor
            if int(new_amount) == new_amount:
                new_amount = int(new_amount)
            return f'{new_amount}{unit}'

        new_instructions = []
        for idx, instruction_step in enumerate(all_instructions):
            new_step = []
            for instruction in instruction_step:
                for pattern in placeholder_patterns:
                    instruction = re.sub(
                        pattern,
                        lambda x: multiply_match(x, factor),
                        instruction
                    )
                new_step.append(instruction)
            new_instructions.append(new_step)

        return new_instructions

    def insert_image(self, page, image, position, height):
        rect = fitz.Rect(
            x0=self.l_padding,
            y0=position,
            x1=self.text_l_padding - self.img_txt_spacing,
            y1=position + height
        )
        page.insert_image(rect, stream=image, keep_proportion=True)

    def insert_textbox(self, page, text, position):
        internal_height = 1000
        rect = fitz.Rect(
            x0=self.text_l_padding,
            y0=position,
            x1=self.width - self.r_padding,
            y1=position + internal_height
        )
        unused_height = page.insert_textbox(
            rect,
            text,
            fontname=self.fontname,
            fontsize=self.fontsize,
            lineheight=self.line_height,
            align=fitz.TEXT_ALIGN_LEFT
        )
        if unused_height < 0:
            self.log.error("Failed to insert text box")
        used_height = internal_height - unused_height
        return used_height


    def insert_page_hero_image(self, pdf, pdf_title):
        pdf_title = pdf_title.replace(' ', '_')
        first_page_img = self.get_center_crop_first_page_img(pdf_title)
        first_page_img_buffer = io.BytesIO()
        first_page_img.save(first_page_img_buffer, format="JPEG")
        first_page_img_buffer.seek(0)
        first_page = pdf.new_page(width=self.width, height=self.width)
        first_page.insert_image(
            fitz.Rect(0, 0, self.width, self.width),
            stream=first_page_img_buffer,
            keep_proportion=True,
        )

    def insert_page_ingredients(self, pdf, recipe_entry, num_meals):
        ingredients = HfMealManager().get_ingredients_shopping_list(
            pd.DataFrame([recipe_entry]),
            num_meals,
            filter_home_ingredients=False,
            sorting='amount'
        )
        internal_height = 9999
        page = pdf.new_page(width=self.width, height=internal_height)
        fitz.Font("spacemo")
        unused_height = page.insert_textbox(
            fitz.Rect(50, 30, self.width, internal_height),
            ingredients,
            fontname="spacemo",
            fontsize=self.fontsize,
            lineheight=self.line_height,
            align=fitz.TEXT_ALIGN_LEFT
        )
        # crop
        used_height = internal_height - unused_height + 50
        rect = page.rect
        cropped_rect = fitz.Rect(rect.x0, rect.y0, rect.x1, used_height)
        page.set_cropbox(cropped_rect)

    def insert_page_with_instructions(self, pdf, recipe_entry, num_meals):
        all_images = self._get_instruction_images(recipe_entry)
        all_instructions = self._get_instructions(recipe_entry, num_meals)
        page = pdf.new_page(width=self.width, height=self.height)
        x_position = local_position = self.t_padding
        for idx, instructions_step in enumerate(all_instructions):
            self.insert_image(page, all_images[idx], x_position, self.step_height)
            for _idx, single_instruction in enumerate(instructions_step):
                used_height = self.insert_textbox(page, single_instruction, position=local_position)
                local_position += used_height + self.paragraph_spacing
            next_x_position = local_position + self.instruction_step_spacing
            minimum_x_position = x_position + self.step_height + self.instruction_step_spacing
            x_position = max(minimum_x_position, next_x_position)
            local_position = x_position
        # crop bottom of pdf to remove empty space
        leftover_height = self.height - x_position
        # print(f"Total Height: {int(x_position)}")
        rect = page.rect
        cropped_rect = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y1 - leftover_height)
        page.set_cropbox(cropped_rect)

    def create_pdf_with_text(self, recipe_entry: pd.Series, num_meals: int):
        pdf_title = PDF_Manager().get_pdf_title(recipe_entry['title'])
        pdf = fitz.open()
        self.insert_page_hero_image(pdf, pdf_title)
        self.insert_page_ingredients(pdf, recipe_entry, num_meals)
        self.insert_page_with_instructions(pdf, recipe_entry, num_meals)
        # save pdf
        os.makedirs(f"{self.save_dir}/{num_meals}", exist_ok=True)
        new_pdf_title = pdf_title.replace('_', ' ')
        pdf.save(f"{self.save_dir}/{num_meals}/{new_pdf_title}.pdf")
        pdf.close()
        return


def create_pdfs(meals: int):
    for i in range(len(recipes_df)):
        recipe_entry = recipes_df.iloc[i]
        print(f"[{i}] Creating PDF for: {recipe_entry['title']}")
        pdf_creator.create_pdf_with_text(recipe_entry, num_meals=meals)
        try:
            pass
        except Exception as e:
            print(f"Error in creating PDF: {e}")


if __name__ == '__main__':
    from threading import Thread
    pdf_manager = PDF_Manager()
    pdf_creator = PDF_Creator()
    recipes_df = pd.read_csv(pdf_manager.csv_data_path)
    for meals in [4, 3, 2, 1, 5, 6]:
        thread = Thread(target=create_pdfs, args=(meals,))
        thread.start()

