from threading import Thread
from selenium import webdriver
from selenium.webdriver.common.by import By

import json
from pandas import DataFrame
import os
from logging import getLogger

from web.driver import create_driver


class SupermarketScraper:
    log = getLogger("Supermarket Scraper")
    num_threads = 20

    def __init__(self):
        self.threads = []
        self.threaded_results = {}

    def get_all_product_links(self, supermarket: str):
        data_dir = f"data/supermarkets/{supermarket}"
        os.makedirs(data_dir, exist_ok=True)
        url = f"https://www.supermarktcheck.de/{supermarket}/sortiment/?page="
        list_elements_selector = ".productListElement"
        driver = create_driver()
        product_links = []
        for i in range(1, 2999):
            self.log.debug(f"Scraping page {i}")
            driver.get(url + str(i))
            products = driver.find_elements(By.CSS_SELECTOR, list_elements_selector)
            if len(products) == 0:
                self.log.info(f"{supermarket}: Found no more products on page {i}")
                break
            for product in products:
                link = product.find_element(By.CSS_SELECTOR, "a")
                product_links.append(link.get_attribute("href"))
        filename = f"{data_dir}/product_links.json"
        with open(filename, "w") as file:
            json.dump(product_links, file)
        return product_links

    def scrape_product(self, url: str, driver: webdriver.Chrome):
        driver.get(url)
        data_selectors = {
            "title": "h1",
            "producer": "#uebersicht dl > dd",
            "prices": "#preise > div:nth-child(2) > table tbody",
            "nutrients": "#naehrwerte > div > div > div:nth-child(1) > div.table-responsive",
            "sellers": "#uebersicht p.sources",
        }
        results = {"url": url}
        for selector in data_selectors:
            try:
                data = driver.find_element(By.CSS_SELECTOR, data_selectors[selector])
                text = data.text
                results[selector] = text
            except Exception:
                results[selector] = None
        return results

    def scrape_products_threaded(self, product_links, driver, thread_id) -> list[dict]:
        all_product_results = []
        for idx, link in enumerate(product_links):
            try:
                product_results = self.scrape_product(link, driver)
                all_product_results.append(product_results)
                self.log.debug(f"[{thread_id}][{idx}] {product_results['producer']} | {product_results['title']}")
            except Exception as e:
                exception_type = type(e).__name__
                self.log.error(f"[{thread_id}][{idx}] {link} | {exception_type}")
        self.threaded_results[thread_id] = all_product_results
        return all_product_results

    def scrape_all_products(self, supermarket: str | None = None):
        self.log.info(f"Scraping {supermarket if supermarket else 'all supermarkets'}")
        data_dir = f"data/supermarkets/{supermarket}" if supermarket else "data/supermarkets"
        os.makedirs(data_dir, exist_ok=True)
        if not os.path.exists(f"{data_dir}/product_links.json"):
            product_links = self.get_all_product_links(supermarket)
        else:
            product_links = json.load(open(f"{data_dir}/product_links.json"))

        all_product_results = []
        self.log.info(f"Scraping {len(product_links)} products")
        for idx in range(self.num_threads):
            thread_webdriver = create_driver(headless=True)
            links_chunk = product_links[idx :: self.num_threads]  # noqa: E203
            thread = Thread(
                target=self.scrape_products_threaded,
                args=(links_chunk, thread_webdriver, idx),
            )
            self.threads.append(thread)
            thread.start()
            self.log.info(f"Thread {idx} started")
        for thread in self.threads:
            thread.join()
        for idx in range(self.num_threads):
            all_product_results.extend(self.threaded_results[idx])
        product_data = DataFrame(all_product_results)
        product_data.to_csv(f"{data_dir}/product_data.csv", index=False)
        return product_data


if __name__ == "__main__":
    scraper = SupermarketScraper()
    scraper.scrape_all_products(supermarket=None)
