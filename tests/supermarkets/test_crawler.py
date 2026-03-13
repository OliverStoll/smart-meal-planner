from supermarkets.crawler import SupermarketScraper


class TestSuperMarketScraper:
    crawler = SupermarketScraper()

    def test_scrape_all_products(self):
        results = self.crawler.scrape_all_products(supermarket="Lidl")
        print(results)
