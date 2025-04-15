import pickle
from time import sleep
from selenium import webdriver

driver = webdriver.Chrome()
driver.get("https://www.supermarktcheck.de/product/214991-rewe-feine-welt-sockeye-graved-wildlachs")
sleep(15)
# Save cookies to a file in binary mode
with open("../data/supermarkets/cookies.pkl", "wb") as file:
    pickle.dump(driver.get_cookies(), file, protocol=pickle.HIGHEST_PROTOCOL)