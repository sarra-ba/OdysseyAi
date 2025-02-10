import scrapy

class EthereumSpider(scrapy.Spider):
    name = "ethereum_spider"

    # Add more URLs to scrape from Ethereum's official site and other sources
    start_urls = [
        'https://ethereum.org/en/energy-consumption/',  # Ethereum's energy consumption page
        'https://blog.ethereum.org/',                   # Ethereum Foundation Blog
        'https://ethereum.org/en/eth2/',                # Ethereum 2.0 page
        'https://ethereum.org/en/community/',          # Community sustainability page
        'https://ethereum.org/en/developers/',          # Developer resources and whitepapers
    ]

    def parse(self, response):
        # Extract headings and paragraphs, as they might contain relevant information
        headings = response.xpath('//h1//text() | //h2//text() | //h3//text()').getall()
        paragraphs = response.xpath('//p//text()').getall()

        # Additional data points for Ethereum
        links = response.xpath('//a/@href').getall()  # Extract links for more resources
        images = response.xpath('//img/@src').getall()  # Extract image URLs if relevant
        articles = response.xpath('//article//text()').getall()  # Extract article content

        # Combine all extracted content into one list
        content = headings + paragraphs + articles + links

        # Filter out any empty strings
        content = [text.strip() for text in content if text.strip()]

        yield {
            'network': 'ethereum',
            'sustainability_info': content,
            'url': response.url,  # Include the URL for context
            'image_links': images,
        }
