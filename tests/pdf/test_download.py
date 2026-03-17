from pdf.download import save_all_pdfs, save_single_pdf


def test_save_all_pdfs(cleaned_recipes):
    save_all_pdfs(recipes=cleaned_recipes[:1])


def test_save_single_pdf(cleaned_recipes):
    save_single_pdf(url=cleaned_recipes.iloc[0]["pdf"], db_ref=".temp/testfile.pdf")
