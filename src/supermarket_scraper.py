from threading import Thread
from selenium import webdriver
from selenium.webdriver.common.by import By
import json
from pandas import DataFrame
import os
from utils.logger import create_logger


class SupermarketScraper:
    log = create_logger("Supermarket Scraper")
    num_threads = 6

    def __init__(self):
        self.threads = []
        self.threaded_results = {}


    def get_all_product_links(self):
        url = "https://www.supermarktcheck.de/lidl/sortiment/?page="
        list_elements_selector = ".productListElement"
        driver = webdriver.Chrome()
        product_links = []
        for i in range(1, 999):
            self.log.debug(f"Scraping page {i}")
            driver.get(url + str(i))
            products = driver.find_elements(By.CSS_SELECTOR, list_elements_selector)
            if len(products) == 0:
                self.log.info(f"Found no more products on page {i}")
                break
            for product in products:
                link = product.find_element(By.CSS_SELECTOR, "a")
                product_links.append(link.get_attribute("href"))
        filename = "data/lidl_product_links.json"
        with open(filename, "w") as file:
            json.dump(product_links, file)
        return product_links


    def scrape_product(self, url: str, driver: webdriver.Chrome):
        driver.get(url)
        data_selectors = {
            'title': "h1",
            'producer': "#uebersicht > div > div > div:nth-child(2) > div:nth-child(5) > div > dl > dd:nth-child(2)",
            'price': "#preise > div:nth-child(2) > table tbody tr:nth-child(1)",
            'nutrients': "#naehrwerte > div > div > div:nth-child(1) > div.table-responsive",
        }
        results = {}
        for selector in data_selectors:
            try:
                data = driver.find_element(By.CSS_SELECTOR, data_selectors[selector])
                results[selector] = data.text
            except:
                results[selector] = None
        return results


    def scrape_products_threaded(self, product_links, driver, thread_id):
        all_product_results = []
        for idx, link in enumerate(product_links):
            product_results = self.scrape_product(link, driver)
            all_product_results.append(product_results)
            self.log.debug(f"[{thread_id}][{idx}] {product_results['producer']} | {product_results['title']}")
        self.threaded_results[thread_id] = all_product_results


    def scrape_all_products(self, supermarket="lidl"):
        driver = webdriver.Chrome()
        os.makedirs(f"data/{supermarket}", exist_ok=True)
        product_links = json.load(open(f"data/{supermarket}/product_links.json"))
        all_product_results = []
        self.log.info(f"Scraping {len(product_links)} products")

        # scrape data threaded
        for idx in range(self.num_threads):
            thread_webdriver = webdriver.Chrome()
            thread = Thread(
                target=self.scrape_products_threaded,
                args=(product_links[idx::self.num_threads], thread_webdriver, idx)
            )
            self.threads.append(thread)
            thread.start()
        for thread in self.threads:
            thread.join()
        for idx in range(self.num_threads):
            all_product_results.extend(self.threaded_results[idx])
        product_data = DataFrame(all_product_results)
        product_data.to_csv(f"data/{supermarket}/product_data.csv")



if __name__ == "__main__":
    SupermarketScraper().scrape_all_products()