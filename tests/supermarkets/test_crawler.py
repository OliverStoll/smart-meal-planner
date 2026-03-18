import pytest

from supermarkets.crawler import SupermarketScraper
from web.driver import create_driver


@pytest.fixture
def supermarket_product_url():
    return "https://www.supermarktcheck.de/product/209354-milram-milch-reis"


@pytest.fixture
def supermarket_name():
    return "bio-company"


@pytest.mark.slow
def test_scrape_all_products(supermarket_name):
    crawler = SupermarketScraper()
    results = crawler.scrape_all_products(supermarket=supermarket_name)
    assert len(results) > 0, f"Expected to find product data for {supermarket_name}, but found none."


@pytest.mark.slow
def test_get_all_product_links(supermarket_name):
    crawler = SupermarketScraper()
    links = crawler.get_all_product_links(supermarket=supermarket_name)
    assert len(links) > 0, f"Expected to find product links for {supermarket_name}, but found none."


@pytest.mark.slow
def test_scrape_product(supermarket_product_url):
    driver = create_driver()
    crawler = SupermarketScraper()
    data = crawler.scrape_product(url=supermarket_product_url, driver=driver)
    assert len(data) > 0, f"Expected to find product data for {supermarket_product_url}, but found none."
    driver.close()


@pytest.mark.slow
def test_scrape_product_threaded(supermarket_product_url):
    driver = create_driver()
    crawler = SupermarketScraper()
    data = crawler.scrape_products_threaded(product_links=[supermarket_product_url], driver=driver, thread_id=1)
    assert len(data) > 0, f"Expected to find product data for {supermarket_product_url}, but found none."
    driver.close()
