from messaging.callbacks.settings import recipe_filter_confirmation_message


def test_recipe_filter_confirmation_message():
    message = recipe_filter_confirmation_message(chat_id=123456789)
    assert message == "Es gibt insgesamt 0 passende Gerichte für deine Einstellungen."
