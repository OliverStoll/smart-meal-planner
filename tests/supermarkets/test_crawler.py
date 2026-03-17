from supermarkets.crawler import SupermarketScraper


def test_scrape_all_products():
    crawler = SupermarketScraper()
    results = crawler.scrape_all_products(supermarket="Lidl")
    print(results)
