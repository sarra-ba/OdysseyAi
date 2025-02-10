import scrapy

class EthereumSpider(scrapy.Spider):
    name = "ethereum_spider"
    start_urls = [
        'https://ethereum.org/en/energy-consumption/',
    ]

    def parse(self, response):
        # Extract headings and paragraphs as before
        headings = response.xpath('//h1//text() | //h2//text() | //h3//text()').getall()
        paragraphs = response.xpath('//p//text()').getall()

        # Combine all extracted content into one list
        content = headings + paragraphs
        
        # Filter out any empty strings
        content = [text.strip() for text in content if text.strip()]

        # Save the extracted content to a JSON file
        yield {
            'page_url': response.url,
            'energy_consumption_info': content
        }

        # Dynamically follow all internal links on the page
        links = response.xpath('//a/@href').getall()
        for link in links:
            # Ensure the link is an internal link (you can adjust this condition)
            if link.startswith('https://ethereum.org/en/'):
                yield response.follow(link, callback=self.parse)
