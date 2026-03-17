def get_pdf_title_from_meal_name(meal_name: str) -> str:
    pdf_title = meal_name.replace(":", "").replace("!", "").replace("&", "und")
    return pdf_title
