import scrapy
import logging

class XRPSpider(scrapy.Spider):
    name = 'xrp_spider'
    start_urls = [
        'https://xrpl.org/blog/2023/aesthetes#why-the-xrp-ledger',
        'https://xrpl.org/about/impact',
        'https://www.xrpl-commons.org/engage/explore-xrp-ledgers-sustainability'
    ]

    def parse(self, response):
        logging.info(f'Processing {response.url}')  # Log the URL being processed
        
        # Extract headings and paragraphs
        headings = response.xpath('//h1//text() | //h2//text() | //h3//text()').getall()
        paragraphs = response.xpath('//p//text()').getall()

        # Extract links and images
        links = response.xpath('//a/@href').getall()
        images = response.xpath('//img/@src').getall()

        # Combine and clean content
        content = headings + paragraphs
        content = [text.strip() for text in content if text.strip()]

        yield {
            'network': 'xrp',
            'sustainability_info': content,
            'url': response.url,
            'image_links': images,
        }
