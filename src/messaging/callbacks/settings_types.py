from dataclasses import dataclass


@dataclass
class SettingsProperties:
    name: str
    friendly_name: str
    options: list[str | int]
    default_value: str | int
    query_message: str
    confirmation_message: str
    option_labels: dict[str, str] = None
    is_filter: bool = False


@dataclass
class UserSettings:
    portions: int = 2
    meal_type: str = "alle"
    max_duration: int = 120
    cal_min: int = 0
