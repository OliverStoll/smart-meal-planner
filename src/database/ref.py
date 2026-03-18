def thumbnail_ref(title: str) -> str:
    return "thumbnails/" + title


def pdf_ref(title: str, num_portions: int) -> str:
    return f"pdfs/{num_portions}/{title.replace('_', ' ')}.pdf"
