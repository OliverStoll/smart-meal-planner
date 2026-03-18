from io import BytesIO
import requests
import pandas as pd
import re
import fitz
from PIL import Image
from logs.logs import create_logger

import messaging.ingredients
from database import CLEANED_RECIPES_REF
from database.engine import df_from_sql
from database.ref import pdf_ref
from database.storage import upload_file
from messaging.utils import get_pdf_title_from_meal_name


class PdfCreator:
    log = create_logger("PDF Creator")
    height = 9999
    text_l_padding = 175
    left_padding = 5
    right_padding = 5
    top_padding = 30
    img_txt_spacing = 10
    width = 600
    step_height = 150
    instruction_step_spacing = 38

    fontname = "helv"
    text_formatting = {
        "fontsize": 26,
        "lineheight": 1.20,
        "align": fitz.TEXT_ALIGN_LEFT,
    }
    fontname_text = "helv"
    fontname_ingredients = "spacemo"

    instruction_img_crop_percentages = (0.26, 0.26, 0.17, 0.18)
    paragraph_spacing = text_formatting["fontsize"] * 1.0
    image_quality = 25
    instruction_divider_color = 0.6

    def __init__(self):
        fitz.Font(self.fontname_ingredients)

    def create_pdf_with_text(self, recipe_entry: pd.Series, num_meals: int):
        pdf_title = get_pdf_title_from_meal_name(recipe_entry["title"])
        pdf = fitz.open()
        self.insert_page_with_ingredients(pdf, recipe_entry, num_meals)
        self.insert_page_with_instructions(pdf, recipe_entry, num_meals)
        self.save_pdf(pdf, num_meals, pdf_title)

    def save_pdf(self, pdf, num_meals, title):
        buffer = BytesIO()
        pdf.save(buffer)
        pdf.close()
        buffer.seek(0)
        ref = pdf_ref(title=title, num_portions=num_meals)
        upload_file(buffer, ref=ref)
        self.log.debug(f"Uploaded pdf for {ref}")
        return

    def insert_page_with_ingredients(
        self,
        pdf: fitz.Document,
        recipe_entry: pd.Series,
        num_meals: int,
        horizontal_padding: int = 50,
        vertical_padding: int = 30,
    ) -> None:
        single_recipe_df = pd.DataFrame([recipe_entry])
        ingredients_text = messaging.ingredients.ingredients_shopping_list(
            recipes=single_recipe_df,
            num_portions=num_meals,
            filter_home_ingredients=False,
        )
        internal_height = 99999
        page = pdf.new_page(width=self.width, height=internal_height)  # type: ignore[attr-defined]
        textbox_rect = fitz.Rect(
            x0=horizontal_padding,
            y0=vertical_padding,
            x1=self.width - horizontal_padding,
            y1=internal_height,
        )
        unused_page_height = page.insert_textbox(
            rect=textbox_rect,
            buffer=ingredients_text,
            fontname="spacemo",
            **self.text_formatting,
        )
        textbox_height = internal_height - unused_page_height
        full_page_height = 2 * vertical_padding + textbox_height
        self._crop_pdf_page_to_height(full_page_height, page)

    def insert_page_with_instructions(self, pdf, recipe_entry, num_meals):
        instruction_images = self._get_instruction_images(recipe_entry["instruction_images"])
        all_instructions = self._get_instructions(recipe_entry, num_meals)
        page = pdf.new_page(width=self.width, height=self.height)
        current_height = self.top_padding
        for idx, instructions_step in enumerate(all_instructions):
            instruction_image = instruction_images[idx] if len(instruction_images) > idx else None
            current_height = self._insert_single_instruction_step(
                page=page,
                instruction_image=instruction_image,
                instructions_step=instructions_step,
                current_height=current_height,
            )
        self._crop_pdf_page_to_height(full_page_height=current_height, page=page)

    def _insert_single_instruction_step(
        self,
        page,
        instruction_image: BytesIO | None,
        instructions_step: list[str],
        current_height: int,
    ):
        """
        Inserts a single instruction step with an image and text into the pdf page.

        Args:
            page: The pdf page to insert the instruction step into.
            instruction_image: The image to insert.
            instructions_step: The list of instructions to insert.
            current_height: The current editing position of the pdf page.
        """
        local_height = current_height
        if instruction_image:
            self.insert_image(
                page=page,
                image=instruction_image,
                page_height=current_height,
                image_height=self.step_height,
            )
        for _idx, single_instruction in enumerate(instructions_step):
            used_height = self.insert_textbox(page, single_instruction, position=local_height)
            local_height += used_height + self.paragraph_spacing
        required_next_height = local_height + self.instruction_step_spacing
        minimum_next_height = current_height + self.step_height + self.instruction_step_spacing
        next_height = max(minimum_next_height, required_next_height)
        self._insert_instruction_step_divider(next_height - self.instruction_step_spacing, page)
        return next_height

    def _insert_instruction_step_divider(self, height, page):
        line_height = 0.5
        line_rect = fitz.Rect(
            x0=self.left_padding * 3,
            y0=height + self.img_txt_spacing,
            x1=self.width - self.right_padding * 3,
            y1=height + line_height + self.img_txt_spacing,
        )
        page.draw_rect(line_rect, color=self.instruction_divider_color, width=line_height)

    def _get_instruction_images(self, image_links: str) -> list[BytesIO]:
        all_images = []
        for idx, image_url in enumerate(image_links):
            if image_url is None or image_url == "":
                self.log.warning(f"Image URL is empty or None for index {idx}: {image_url}")
                all_images.append(None)
                continue
            try:
                image = Image.open(BytesIO(requests.get(image_url).content))
                image = self.crop_image_percentages(image, *self.instruction_img_crop_percentages)
                img_buffer = BytesIO()
                image.save(img_buffer, format="JPEG", quality=self.image_quality)
                img_buffer.seek(0)
            except Exception as e:
                self.log.error(f"Error in converting image: {e}")
                img_buffer = None
            all_images.append(img_buffer)
        return all_images

    def _get_instructions(self, recipe_entry: pd.Series, num_meals: int) -> list[list[str]]:
        """Replaces all placeholders in the instructions with the correct values (with and without unit)"""

        def multiply_match(match, factor):
            amount = int(match.group(1))
            unit = " " + match.group(2) if len(match.groups()) > 1 else ""
            new_amount = amount * factor
            if int(new_amount) == new_amount:
                new_amount = int(new_amount)
            return f"{new_amount}{unit}"

        all_instructions = recipe_entry["instructions"]
        placeholder_patterns = [r"\[(\d+)\s*(\w+)\]", r"\[(\d+)\s*\w*\]"]
        factor = num_meals / 2
        new_instructions = []
        for idx, instruction_step in enumerate(all_instructions):
            new_step = []
            for instruction in instruction_step:
                for pattern in placeholder_patterns:
                    instruction = re.sub(pattern, lambda x: multiply_match(x, factor), instruction)
                new_step.append(instruction)
            new_instructions.append(new_step)

        return new_instructions

    def insert_image(self, page, image: BytesIO, page_height: int, image_height: int):
        right_padding = self.text_l_padding - self.img_txt_spacing
        rect = fitz.Rect(
            x0=self.left_padding,
            y0=page_height,
            x1=right_padding,
            y1=page_height + image_height,
        )
        page.insert_image(rect, stream=image, keep_proportion=True)

    def insert_textbox(self, page, text, position):
        internal_height = 1000
        rect = fitz.Rect(
            x0=self.text_l_padding,
            y0=position,
            x1=self.width - self.right_padding,
            y1=position + internal_height,
        )
        unused_height = page.insert_textbox(rect, text, fontname="helv", **self.text_formatting)
        used_height = internal_height - unused_height
        return used_height

    @staticmethod
    def _crop_pdf_page_to_height(full_page_height: int, page: fitz.Page) -> None:
        fitted_page_rect = fitz.Rect(x0=page.rect.x0, y0=page.rect.y0, x1=page.rect.x1, y1=full_page_height)
        page.set_cropbox(fitted_page_rect)

    @staticmethod
    def crop_image_percentages(img: Image, left: float, right: float, top: float, bottom: float) -> Image:
        """Crops an image with given percentages of the image size from each side"""
        width, height = img.size
        left = int(left * width)
        top = int(top * height)
        right = width - int(right * width)
        bottom = height - int(bottom * height)
        return img.crop((left, top, right, bottom))


def create_pdfs(recipes: pd.DataFrame, num_meals: int):
    pdf_creator = PdfCreator()
    for i in range(len(recipes)):
        recipe_entry = recipes.iloc[i]
        print(f"[{i}] Creating [meals:{num_meals}] PDF for: {recipe_entry['title']}")
        try:
            pdf_creator.create_pdf_with_text(recipe_entry, num_meals=num_meals)
        except Exception as e:
            print(f"Error in creating PDF: {e}")


def create_pdfs_threaded(recipes: pd.DataFrame, num_meals: list[int], num_threads_per_mealsize: int = 2):
    from threading import Thread
    import numpy as np

    threads = []
    for num_meal in num_meals:
        meal_recipes_split = np.array_split(recipes, num_threads_per_mealsize)
        for idx, meal_recipes in enumerate(meal_recipes_split, start=1):
            thread = Thread(
                target=create_pdfs,
                kwargs={"recipes": meal_recipes, "num_meals": num_meal},
            )
            thread.start()
            threads.append(thread)
    for thread in threads:
        thread.join()
    print("All threads completed.")


if __name__ == "__main__":
    create_pdfs_threaded(
        recipes=df_from_sql(CLEANED_RECIPES_REF),
        num_meals=[1, 2, 3, 4, 5, 6],
        num_threads_per_mealsize=4,
    )
