from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def create_driver(headless: bool = True):
    options = Options()
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_argument("--log-level=3")
    if headless:
        options.add_argument("--headless")
    return webdriver.Chrome(options=options)
