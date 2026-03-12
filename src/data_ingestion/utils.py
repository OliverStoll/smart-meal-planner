from selenium.webdriver.chrome.webdriver import WebDriver


def scroll_driver_down(driver: WebDriver):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
