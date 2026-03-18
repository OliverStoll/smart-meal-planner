from messaging.callbacks.settings_types import UserSettings, SettingsProperties


class TestUserSettings:
    def test_default_portions(self):
        settings = UserSettings()
        assert settings.portions == 2

    def test_default_meal_type(self):
        settings = UserSettings()
        assert settings.meal_type == "alle"

    def test_default_max_duration(self):
        settings = UserSettings()
        assert settings.max_duration == 120

    def test_default_cal_min(self):
        settings = UserSettings()
        assert settings.cal_min == 0

    def test_custom_values(self):
        settings = UserSettings(portions=4, meal_type="vegan", max_duration=30, cal_min=500)
        assert settings.portions == 4
        assert settings.meal_type == "vegan"
        assert settings.max_duration == 30
        assert settings.cal_min == 500

    def test_is_dataclass(self):
        settings = UserSettings(portions=3)
        assert settings.portions == 3


class TestSettingsProperties:
    def test_required_fields(self):
        props = SettingsProperties(
            name="portions",
            friendly_name="Portionsanzahl",
            options=[1, 2, 3],
            default_value=2,
            query_message="Choose portions:",
            confirmation_message="You chose {value} portions.",
        )
        assert props.name == "portions"
        assert props.friendly_name == "Portionsanzahl"
        assert props.options == [1, 2, 3]
        assert props.default_value == 2
        assert props.query_message == "Choose portions:"
        assert props.confirmation_message == "You chose {value} portions."

    def test_optional_fields_default_to_none(self):
        props = SettingsProperties(
            name="meal_type",
            friendly_name="Art der Gerichte",
            options=["alle", "vegan"],
            default_value="alle",
            query_message="Choose type:",
            confirmation_message="Type: {value}",
        )
        assert props.option_labels is None
        assert props.is_filter is False

    def test_with_option_labels(self):
        labels = {"alle": "all", "vegan": "vegan"}
        props = SettingsProperties(
            name="meal_type",
            friendly_name="Art der Gerichte",
            options=["alle", "vegan"],
            default_value="alle",
            query_message="Choose type:",
            confirmation_message="Type: {value}",
            option_labels=labels,
            is_filter=True,
        )
        assert props.option_labels == labels
        assert props.is_filter is True
