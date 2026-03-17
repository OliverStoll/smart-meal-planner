from pdf.creation import create_pdfs, PdfCreator, create_pdfs_threaded
from pdf.download import remove_recipes_with_faulty_pdfs


def test_create_pdfs(cleaned_recipes):
    create_pdfs(recipes=cleaned_recipes[:1], num_meals=1)


def test_create_pdf_with_text(cleaned_recipes):
    creator = PdfCreator()
    creator.create_pdf_with_text(cleaned_recipes.iloc[0], num_meals=1)


def test_create_pdfs_threaded(cleaned_recipes):
    create_pdfs_threaded(
        recipes=cleaned_recipes[:1], num_meals=[1], num_threads_per_mealsize=1
    )


def test_remove_recipes_with_faulty_pdfs(cleaned_recipes):
    checked_recipes = remove_recipes_with_faulty_pdfs(cleaned_recipes)
    assert len(checked_recipes) == 0
