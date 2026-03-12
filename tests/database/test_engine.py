import pytest
from unittest.mock import patch
from database.engine import table


class TestTable:
    def test_table_returns_prefixed_name(self):
        with patch("database.engine.PROJECT_NAME", "test_project"):
            result = table("recipes")
        assert result == "test_project-recipes"

    def test_table_with_default_project_name(self):
        result = table("ingredients")
        assert "-ingredients" in result
        assert result.endswith("ingredients")

    def test_table_includes_table_name(self):
        result = table("users")
        assert "users" in result

    def test_table_format_is_prefix_dash_name(self):
        with patch("database.engine.PROJECT_NAME", "myapp"):
            result = table("sessions")
        assert result == "myapp-sessions"
