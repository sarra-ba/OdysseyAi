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
    # Add more user agents if needed
]

class CardanoSustainabilitySpider(scrapy.Spider):
    name = 'cardano_sustainability_spider'
    allowed_domains = ['cardano.org']
    start_urls = [
        'https://cardano.org/',
        'https://cardano.org/ouroboros'
        
    ]

    # Add custom headers to simulate a real browser request
    custom_settings = {
        'USER_AGENT': random.choice(USER_AGENT_LIST),
        'ROBOTSTXT_OBEY': False,  # Bypass robots.txt (use with caution)
        'DOWNLOAD_DELAY': 2,  # Add delay to avoid overwhelming the server
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy_selenium.SeleniumMiddleware': 800,  # Enable Selenium middleware for JavaScript content (if needed)
        },
        'SELENIUM_DRIVER_NAME': 'chrome',
        'SELENIUM_DRIVER_EXECUTABLE_PATH': None,  # Remove executable_path and use Service instead
        'SELENIUM_DRIVER_ARGUMENTS': ['--headless', '--disable-gpu', '--no-sandbox'],
    }

    def __init__(self, *args, **kwargs):
        super(CardanoSustainabilitySpider, self).__init__(*args, **kwargs)
        # Set up Selenium WebDriver
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.get_chrome_options())

    def get_chrome_options(self):
        chrome_options = webdriver.ChromeOptions()
        for arg in self.custom_settings['SELENIUM_DRIVER_ARGUMENTS']:
            chrome_options.add_argument(arg)
        return chrome_options

    def start_requests(self):
        # Make initial requests using SeleniumRequest
        for url in self.start_urls:
            yield SeleniumRequest(
                url=url,
                callback=self.parse,
                wait_time=3,  # Wait for the page to load
                screenshot=False  # Disable screenshot for debugging (optional)
            )

    def parse(self, response):
        # Extract headings (h1, h2, h3)
        headings = response.xpath('//h1//text()').getall() + response.xpath('//h2//text()').getall() + response.xpath('//h3//text()').getall()
        headings = [heading.strip() for heading in headings if heading.strip()]

        # Extract paragraphs (p)
        paragraphs = response.xpath('//p//text()').getall()
        paragraphs = [para.strip() for para in paragraphs if para.strip()]

        # Extract image links (img tags with src attribute)
        image_links = response.xpath('//img/@src').getall()

        # Extract links (anchor tags with href attribute)
        links = response.xpath('//a/@href').getall()

        # Create the scraped item
        yield {
            'network': 'cardano',
            'sustainability_info': {
                'headings': headings,
                'paragraphs': paragraphs,
                'image_links': image_links,
                'links': links
            },
            'url': response.url
        }

    def closed(self, reason):
        # Clean up the Selenium driver when the spider is closed
        self.driver.quit()
