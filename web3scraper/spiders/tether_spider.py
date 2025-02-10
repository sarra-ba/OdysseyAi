import scrapy

class TetherSpider(scrapy.Spider):
    name = "tether_spider"
    start_urls = [
        'https://tether.io/power/',
        'https://tether.recruitee.com/power',
    ]

    def parse(self, response):
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
            'network': 'tether',
            'sustainability_info': content,
            'url': response.url,
            'image_links': images,
        }
