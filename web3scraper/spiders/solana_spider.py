import scrapy
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from scrapy_selenium import SeleniumRequest

# List of user agents to rotate
USER_AGENT_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/92.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/92.0.902.67',
]

class SolanaSustainabilitySpider(scrapy.Spider):
    name = 'solana_sustainability_spider'
    allowed_domains = ['climate.solana.com']
    start_urls = ['https://climate.solana.com/methodology']

    custom_settings = {
        'USER_AGENT': random.choice(USER_AGENT_LIST),
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_DELAY': 2,
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy_selenium.SeleniumMiddleware': 800,
        },
        'SELENIUM_DRIVER_NAME': 'chrome',
        'SELENIUM_DRIVER_EXECUTABLE_PATH': None,
        'SELENIUM_DRIVER_ARGUMENTS': ['--headless', '--disable-gpu', '--no-sandbox'],
    }

    def __init__(self, *args, **kwargs):
        super(SolanaSustainabilitySpider, self).__init__(*args, **kwargs)
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.get_chrome_options())

    def get_chrome_options(self):
        chrome_options = webdriver.ChromeOptions()
        for arg in self.custom_settings['SELENIUM_DRIVER_ARGUMENTS']:
            chrome_options.add_argument(arg)
        return chrome_options

    def start_requests(self):
        for url in self.start_urls:
            yield SeleniumRequest(
                url=url,
                callback=self.parse,
                wait_time=3
            )

    def parse(self, response):
        headings = response.xpath('//h1//text()').getall() + response.xpath('//h2//text()').getall() + response.xpath('//h3//text()').getall()
        headings = [heading.strip() for heading in headings if heading.strip()]

        paragraphs = response.xpath('//p//text()').getall()
        paragraphs = [para.strip() for para in paragraphs if para.strip()]

        image_links = response.xpath('//img/@src').getall()
        links = response.xpath('//a/@href').getall()

        yield {
            'network': 'solana',
            'sustainability_info': {
                'headings': headings,
                'paragraphs': paragraphs,
                'image_links': image_links,
                'links': links
            },
            'url': response.url
        }

    def closed(self, reason):
        self.driver.quit()
