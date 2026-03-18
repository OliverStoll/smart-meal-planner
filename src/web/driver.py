from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


def create_driver(headless: bool = True):
    options = Options()
    if headless:
        options.add_argument("--headless")
    return webdriver.Chrome(options=options)
