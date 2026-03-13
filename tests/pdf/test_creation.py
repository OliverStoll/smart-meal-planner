import io
import pytest
import pandas as pd
from PIL import Image
from unittest.mock import MagicMock, patch

from pdf.creation import PdfCreator, create_pdfs, create_pdfs_threaded


def _make_fake_image(width=100, height=100):
    """Create a simple RGB PIL image for testing."""
    return Image.new("RGB", (width, height), color=(128, 64, 32))


def _make_jpeg_bytes(width=200, height=200):
    """Return bytes of a JPEG-encoded image."""
    img = _make_fake_image(width, height)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.read()


@pytest.fixture
def pdf_creator():
    """Create a PdfCreator with mocked __init__ dependencies."""

    def fake_init(self, save_dir="/tmp/test_pdfs"):
        self.save_dir = save_dir
        self.meal_manager = MagicMock()

    with patch.object(PdfCreator, "__init__", fake_init):
        creator = PdfCreator()
    return creator


@pytest.fixture
def sample_recipe_entry():
    """Sample recipe pd.Series with instructions that contain placeholders."""
    return pd.Series({
        "title": "Pasta Primavera",
        "instructions": str([
            ["Add [2 cups] of water.", "Boil."],
            ["Add [100 g] of pasta."],
        ]),
        "instruction_images": str(["http://example.com/img1.jpg", None, ""]),
        "ingredients": str([
            {"name": "Pasta", "quantity": "200", "unit": "g"},
            {"name": "Water", "quantity": "500", "unit": "ml"},
        ]),
    })


# ---------------------------------------------------------------------------
# TestCropImagePercentages
# ---------------------------------------------------------------------------

class TestCropImagePercentages:
    def test_no_crop_returns_original_size(self):
        img = _make_fake_image(100, 100)
        result = PdfCreator.crop_image_percentages(img, 0.0, 0.0, 0.0, 0.0)
        assert result.size == (100, 100)

    def test_symmetric_crop(self):
        img = _make_fake_image(100, 100)
        result = PdfCreator.crop_image_percentages(img, 0.1, 0.1, 0.1, 0.1)
        assert result.size == (80, 80)

    def test_crop_left_only(self):
        img = _make_fake_image(100, 80)
        result = PdfCreator.crop_image_percentages(img, 0.2, 0.0, 0.0, 0.0)
        assert result.size == (80, 80)

    def test_crop_top_only(self):
        img = _make_fake_image(100, 80)
        result = PdfCreator.crop_image_percentages(img, 0.0, 0.0, 0.25, 0.0)
        assert result.size == (100, 60)

    def test_crop_right_only(self):
        img = _make_fake_image(100, 80)
        result = PdfCreator.crop_image_percentages(img, 0.0, 0.2, 0.0, 0.0)
        assert result.size == (80, 80)

    def test_crop_bottom_only(self):
        img = _make_fake_image(100, 80)
        result = PdfCreator.crop_image_percentages(img, 0.0, 0.0, 0.0, 0.25)
        assert result.size == (100, 60)

    def test_returns_pil_image(self):
        img = _make_fake_image(200, 150)
        result = PdfCreator.crop_image_percentages(img, 0.1, 0.1, 0.1, 0.1)
        assert isinstance(result, Image.Image)


# ---------------------------------------------------------------------------
# TestGetInstructions
# ---------------------------------------------------------------------------

class TestGetInstructions:
    def test_preserves_structure(self, pdf_creator, sample_recipe_entry):
        result = pdf_creator._get_instructions(sample_recipe_entry, num_meals=2)
        assert len(result) == 2
        assert len(result[0]) == 2
        assert len(result[1]) == 1

    def test_returns_list_of_lists(self, pdf_creator, sample_recipe_entry):
        result = pdf_creator._get_instructions(sample_recipe_entry, num_meals=2)
        assert isinstance(result, list)
        for step in result:
            assert isinstance(step, list)

    def test_factor_one_keeps_original_quantity(self, pdf_creator, sample_recipe_entry):
        result = pdf_creator._get_instructions(sample_recipe_entry, num_meals=2)
        assert "2 cups" in result[0][0]

    def test_doubles_quantity_for_four_meals(self, pdf_creator, sample_recipe_entry):
        result = pdf_creator._get_instructions(sample_recipe_entry, num_meals=4)
        assert "4 cups" in result[0][0]

    def test_halves_quantity_for_one_meal(self, pdf_creator, sample_recipe_entry):
        # The code multiplies without grammar correction, so "2 cups" halved → "1 cups"
        result = pdf_creator._get_instructions(sample_recipe_entry, num_meals=1)
        assert "1 cups" in result[0][0]

    def test_integer_result_has_no_decimal(self, pdf_creator):
        entry = pd.Series({
            "instructions": str([["Add [3 cups] of sugar."]]),
        })
        result = pdf_creator._get_instructions(entry, num_meals=4)
        assert "6 cups" in result[0][0]
        assert "6.0" not in result[0][0]

    def test_replaces_quantity_with_unit(self, pdf_creator, sample_recipe_entry):
        result = pdf_creator._get_instructions(sample_recipe_entry, num_meals=4)
        assert "200 g" in result[1][0]

    def test_brackets_are_removed_from_placeholders(self, pdf_creator, sample_recipe_entry):
        result = pdf_creator._get_instructions(sample_recipe_entry, num_meals=2)
        for step in result:
            for instruction in step:
                assert "[" not in instruction and "]" not in instruction


# ---------------------------------------------------------------------------
# TestGetInstructionImages
# ---------------------------------------------------------------------------

class TestGetInstructionImages:
    def test_returns_none_for_empty_string_url(self, pdf_creator):
        result = pdf_creator._get_instruction_images(str([""]))
        assert result[0] is None

    def test_returns_none_for_none_url(self, pdf_creator):
        result = pdf_creator._get_instruction_images(str([None]))
        assert result[0] is None

    def test_list_length_matches_input(self, pdf_creator):
        result = pdf_creator._get_instruction_images(str(["", None, ""]))
        assert len(result) == 3

    def test_returns_bytesio_for_valid_image(self, pdf_creator):
        mock_response = MagicMock()
        mock_response.content = _make_jpeg_bytes()
        with patch("pdf.creation.requests.get", return_value=mock_response):
            result = pdf_creator._get_instruction_images(str(["http://example.com/image.jpg"]))
        assert len(result) == 1
        assert isinstance(result[0], io.BytesIO)

    def test_appends_none_on_download_error(self, pdf_creator):
        with patch("pdf.creation.requests.get", side_effect=Exception("Network error")):
            result = pdf_creator._get_instruction_images(str(["http://example.com/broken.jpg"]))
        assert result[0] is None

    def test_mixed_valid_and_empty_urls(self, pdf_creator):
        mock_response = MagicMock()
        mock_response.content = _make_jpeg_bytes()
        with patch("pdf.creation.requests.get", return_value=mock_response):
            result = pdf_creator._get_instruction_images(str(["http://example.com/img.jpg", ""]))
        assert isinstance(result[0], io.BytesIO)
        assert result[1] is None


# ---------------------------------------------------------------------------
# TestInsertImage
# ---------------------------------------------------------------------------

class TestInsertImage:
    def test_calls_insert_image_on_page(self, pdf_creator):
        mock_page = MagicMock()
        fake_image = io.BytesIO(b"fake_image_data")
        pdf_creator.insert_image(mock_page, fake_image, page_height=100, image_height=150)
        mock_page.insert_image.assert_called_once()

    def test_uses_keep_proportion(self, pdf_creator):
        mock_page = MagicMock()
        fake_image = io.BytesIO(b"fake_image_data")
        pdf_creator.insert_image(mock_page, fake_image, page_height=0, image_height=150)
        call_kwargs = mock_page.insert_image.call_args.kwargs
        assert call_kwargs.get("keep_proportion") is True

    def test_passes_stream_to_insert_image(self, pdf_creator):
        mock_page = MagicMock()
        fake_image = io.BytesIO(b"fake_image_data")
        pdf_creator.insert_image(mock_page, fake_image, page_height=0, image_height=100)
        call_kwargs = mock_page.insert_image.call_args.kwargs
        assert call_kwargs.get("stream") is fake_image


# ---------------------------------------------------------------------------
# TestInsertTextbox
# ---------------------------------------------------------------------------

class TestInsertTextbox:
    def test_calls_insert_textbox_on_page(self, pdf_creator):
        mock_page = MagicMock()
        mock_page.insert_textbox.return_value = 500
        pdf_creator.insert_textbox(mock_page, "Sample text", position=100)
        mock_page.insert_textbox.assert_called_once()

    def test_returns_used_height(self, pdf_creator):
        mock_page = MagicMock()
        mock_page.insert_textbox.return_value = 700
        used_height = pdf_creator.insert_textbox(mock_page, "text", position=0)
        assert used_height == 300  # 1000 - 700

    def test_used_height_of_zero_when_full_textbox(self, pdf_creator):
        mock_page = MagicMock()
        mock_page.insert_textbox.return_value = 1000
        used_height = pdf_creator.insert_textbox(mock_page, "text", position=0)
        assert used_height == 0


# ---------------------------------------------------------------------------
# TestCropPdfPageToHeight
# ---------------------------------------------------------------------------

class TestCropPdfPageToHeight:
    def test_sets_cropbox_y1_to_given_height(self):
        import fitz
        pdf = fitz.open()
        page = pdf.new_page(width=600, height=9999)
        PdfCreator._crop_pdf_page_to_height(500, page)
        assert page.cropbox.y1 == 500
        pdf.close()

    def test_preserves_x0_and_y0(self):
        import fitz
        pdf = fitz.open()
        page = pdf.new_page(width=600, height=9999)
        PdfCreator._crop_pdf_page_to_height(300, page)
        assert page.cropbox.x0 == 0
        assert page.cropbox.y0 == 0
        pdf.close()

    def test_preserves_x1(self):
        import fitz
        pdf = fitz.open()
        page = pdf.new_page(width=600, height=9999)
        PdfCreator._crop_pdf_page_to_height(300, page)
        assert page.cropbox.x1 == 600
        pdf.close()


# ---------------------------------------------------------------------------
# TestInsertInstructionStepDivider
# ---------------------------------------------------------------------------

class TestInsertInstructionStepDivider:
    def test_calls_draw_rect_on_page(self, pdf_creator):
        mock_page = MagicMock()
        pdf_creator._insert_instruction_step_divider(height=200, page=mock_page)
        mock_page.draw_rect.assert_called_once()

    def test_passes_color_to_draw_rect(self, pdf_creator):
        mock_page = MagicMock()
        pdf_creator._insert_instruction_step_divider(height=200, page=mock_page)
        call_kwargs = mock_page.draw_rect.call_args.kwargs
        assert call_kwargs.get("color") == pdf_creator.instruction_divider_color


# ---------------------------------------------------------------------------
# TestInsertSingleInstructionStep
# ---------------------------------------------------------------------------

class TestInsertSingleInstructionStep:
    def test_inserts_image_when_provided(self, pdf_creator):
        mock_page = MagicMock()
        mock_page.insert_textbox.return_value = 900
        fake_image = io.BytesIO(b"img")
        with patch.object(pdf_creator, "insert_image") as mock_insert_image:
            with patch.object(pdf_creator, "_insert_instruction_step_divider"):
                pdf_creator._insert_single_instruction_step(
                    page=mock_page,
                    instruction_image=fake_image,
                    instructions_step=["Step 1"],
                    current_height=0,
                )
        mock_insert_image.assert_called_once()

    def test_skips_image_when_none(self, pdf_creator):
        mock_page = MagicMock()
        mock_page.insert_textbox.return_value = 900
        with patch.object(pdf_creator, "insert_image") as mock_insert_image:
            with patch.object(pdf_creator, "_insert_instruction_step_divider"):
                pdf_creator._insert_single_instruction_step(
                    page=mock_page,
                    instruction_image=None,
                    instructions_step=["Step 1"],
                    current_height=0,
                )
        mock_insert_image.assert_not_called()

    def test_returns_next_height_greater_than_current(self, pdf_creator):
        mock_page = MagicMock()
        mock_page.insert_textbox.return_value = 900
        with patch.object(pdf_creator, "_insert_instruction_step_divider"):
            result = pdf_creator._insert_single_instruction_step(
                page=mock_page,
                instruction_image=None,
                instructions_step=["Step 1"],
                current_height=50,
            )
        assert result > 50

    def test_inserts_textbox_for_each_instruction(self, pdf_creator):
        mock_page = MagicMock()
        mock_page.insert_textbox.return_value = 900
        with patch.object(pdf_creator, "_insert_instruction_step_divider"):
            pdf_creator._insert_single_instruction_step(
                page=mock_page,
                instruction_image=None,
                instructions_step=["Line 1", "Line 2", "Line 3"],
                current_height=0,
            )
        assert mock_page.insert_textbox.call_count == 3

    def test_inserts_divider(self, pdf_creator):
        mock_page = MagicMock()
        mock_page.insert_textbox.return_value = 900
        with patch.object(pdf_creator, "_insert_instruction_step_divider") as mock_divider:
            pdf_creator._insert_single_instruction_step(
                page=mock_page,
                instruction_image=None,
                instructions_step=["Step 1"],
                current_height=0,
            )
        mock_divider.assert_called_once()


# ---------------------------------------------------------------------------
# TestCreatePdfs
# ---------------------------------------------------------------------------

class TestCreatePdfs:
    def test_calls_create_pdf_with_text_for_each_recipe(self):
        recipes = pd.DataFrame({
            "title": ["Recipe A", "Recipe B"],
        })
        mock_creator = MagicMock()
        with patch("pdf.creation.PdfCreator", return_value=mock_creator):
            create_pdfs(recipes, num_meals=2)
        assert mock_creator.create_pdf_with_text.call_count == 2

    def test_handles_exception_per_recipe_without_raising(self):
        recipes = pd.DataFrame({"title": ["Recipe A"]})
        mock_creator = MagicMock()
        mock_creator.create_pdf_with_text.side_effect = Exception("Creation failed")
        with patch("pdf.creation.PdfCreator", return_value=mock_creator):
            create_pdfs(recipes, num_meals=2)  # must not raise

    def test_passes_num_meals_to_create_pdf_with_text(self):
        recipes = pd.DataFrame({"title": ["Recipe A"]})
        mock_creator = MagicMock()
        with patch("pdf.creation.PdfCreator", return_value=mock_creator):
            create_pdfs(recipes, num_meals=4)
        _, call_kwargs = mock_creator.create_pdf_with_text.call_args
        assert call_kwargs.get("num_meals") == 4


# ---------------------------------------------------------------------------
# TestCreatePdfsThreaded
# ---------------------------------------------------------------------------

class TestCreatePdfsThreaded:
    def test_completes_without_error(self):
        recipes = pd.DataFrame({"title": ["Recipe A", "Recipe B"]})
        mock_creator = MagicMock()
        with patch("pdf.creation.PdfCreator", return_value=mock_creator):
            create_pdfs_threaded(recipes, num_meals=[2], num_threads_per_mealsize=1)

    def test_calls_create_pdf_with_text_for_all_meal_sizes(self):
        recipes = pd.DataFrame({"title": ["Recipe A"]})
        mock_creator = MagicMock()
        with patch("pdf.creation.PdfCreator", return_value=mock_creator):
            create_pdfs_threaded(recipes, num_meals=[2, 4], num_threads_per_mealsize=1)
        # 2 meal sizes × 1 recipe each = at least 2 calls
        assert mock_creator.create_pdf_with_text.call_count >= 2
