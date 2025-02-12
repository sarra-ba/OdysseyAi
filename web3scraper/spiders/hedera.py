import scrapy
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from scrapy_selenium import SeleniumRequest
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import time

# List of user agents to rotate
USER_AGENT_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/92.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/92.0.902.67',
]

class HederaSustainabilitySpider(scrapy.Spider):
    name = 'hedera_sustainability_spider'
    allowed_domains = ['hedera.com', 'hbarfoundation.org']
    start_urls = [
        'https://hedera.com/use-cases/sustainability',
        'https://www.hbarfoundation.org/apply',
        'https://hedera.com/ucl-blockchain-energy',
        'https://hedera.com/learning/sustainability/nft-sustainability'
    ]

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
        super(HederaSustainabilitySpider, self).__init__(*args, **kwargs)
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=self.get_chrome_options()
        )

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
                wait_time=3,
                screenshot=False
            )

    def parse(self, response):
        self.scroll_to_bottom()

        headings = response.xpath('//h1//text() | //h2//text() | //h3//text()').getall()
        headings = [heading.strip() for heading in headings if heading.strip()]

        paragraphs = response.xpath('//p//text()').getall()
        paragraphs = [para.strip() for para in paragraphs if para.strip()]

        links = response.xpath('//a/@href').getall()

        combined_text = '\n'.join(headings + paragraphs)

        yield {
            'company': 'Hedera',  # Set company name to Hedera
            'network': 'hedera',
            'text': combined_text,
            'sustainability_info': {
                'headings': headings,
                'paragraphs': paragraphs,
                'links': links
            },
            'url': response.url
        }

    def scroll_to_bottom(self):
        body = self.driver.find_element(By.TAG_NAME, 'body')
        for _ in range(3):
            body.send_keys(Keys.END)
            time.sleep(2)

    def closed(self, reason):
        self.driver.quit()
