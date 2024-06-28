import json
import copy
import re
import asyncio
import unicodedata
import sys

from datetime import datetime, timezone

from temporalio import activity

from bs4 import BeautifulSoup, SoupStrainer

from elasticsearch import AsyncElasticsearch
from langchain_elasticsearch import ElasticsearchStore
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveJsonSplitter
from langchain_core.documents import Document

from playwright.async_api import async_playwright, Page, ElementHandle

from typing import TypedDict, Optional, Any, Coroutine

from urllib.parse import urljoin

from amazoncaptcha import AmazonCaptcha

# from kafka import KafkaProducer
# from kafka.errors import KafkaError


class SearchResult(TypedDict):

    product_link: str
    is_sponsored: bool


class ProductImage(TypedDict):

    thumbnail_url: str
    image_url: str


class UserReview(TypedDict):

    review_date: str
    review_body: str
    review_rating: int


class ProductInfoDoc(TypedDict):

    title: str
    product_title: str
    price_symbol: str
    price: str
    description: Optional[str]
    details: dict[str, str]


def is_tag_a_product_info(elem: str, attrs: dict[str, str]) -> bool:

    html_id = attrs.get("id", "")
    css_classes = attrs.get("class", "").split(" ")

    return any(
        [
            elem == "h1" and html_id == "title",
            elem == "div" and html_id == "productDescription",
            # elem == "div" and html_id == "imgTagWrapperId",
            elem == "span" and "priceToPay" in css_classes,
            elem == "table" and "prodDetTable" in css_classes,
            # elem == "li" and "imageThumbnail" in css_classes,
            # elem == "a" and "see-all-reviews-link-foot" in css_classes,
            # elem == "div" and "review" in css_classes,
        ]
    )


all_chars = (chr(i) for i in range(sys.maxunicode))
control_chars_categories = {"Cc", "Cf", "Cn", "Co", "Cs", "Zp"}
control_chars = "".join(
    c for c in all_chars if unicodedata.category(c) in control_chars_categories
)

control_char_re = re.compile("[%s]" % re.escape(control_chars))


def remove_control_chars(s: str) -> str:
    return control_char_re.sub("", s)


def product_html_to_info_doc(product_html: BeautifulSoup) -> ProductInfoDoc:

    product_info: ProductInfoDoc = {
        "description": None,
    }

    title_span = product_html.select_one("span#productTitle")

    if title_span is None:
        raise ValueError("Product title not found")

    product_info["title"] = title_span.text.strip()

    description_span = product_html.select_one("div#productDescription p span")

    if description_span is not None:
        product_info["description"] = description_span.text.strip("\n ")

    price_symbol = product_html.select_one("span.a-price-symbol")
    price_whole = product_html.select_one("span.a-price-whole")
    price_fraction = product_html.select_one("span.a-price-fraction")

    if price_symbol is None or price_whole is None or price_fraction is None:
        raise ValueError("Product price not found")

    product_info["price_symbol"] = price_symbol.text
    price_whole_number = re.sub(r"\D+", "", price_whole.text)

    product_info["price"] = f"{price_whole_number}.{price_fraction.text}"

    details_tables = product_html.select("table.prodDetTable")

    product_info["details"] = {}

    for table in details_tables:

        rows = table.select("tr")

        for row in rows:

            attribute_name = remove_control_chars(row.select_one("th").text).strip(
                "\n "
            )
            attribute_value = remove_control_chars(row.select_one("td").text).strip(
                "\n "
            )

            product_info["details"][attribute_name] = attribute_value

    return product_info


class AmazonBrazilScraping:

    amazon_url: str = "https://www.amazon.com.br"
    
    embedding_size: int = 1536

    def __init__(
        self,
        elasticsearch_client: AsyncElasticsearch,
        openai_embeddings: OpenAIEmbeddings,
        headless: bool = False,
        vector_index_alias: str = "products-vector-brazil-amazon",
    ):
        self.headless = headless

        self.openai_embeddings = openai_embeddings

        self.vector_index_alias = vector_index_alias
        
        self.elasticsearch_client = elasticsearch_client

        self.json_splitter = RecursiveJsonSplitter(
            max_chunk_size=self.embedding_size,
        )

    @activity.defn(name="amazon_brazil_scraping_search")
    async def search(
        self, search_term: str, page: int, geolocation: tuple[float, float]
    ) -> list[SearchResult]:
        async with async_playwright() as p:

            browser = await p.chromium.launch(headless=self.headless)

            latitude, longitude = geolocation

            context = await browser.new_context(
                geolocation={"latitude": latitude, "longitude": longitude},
                permissions=["geolocation"],
            )

            page: Page = await context.new_page()

            await page.goto(self.amazon_url)
            
            await self.__wait_for_captcha(page, page.wait_for_selector("input#twotabsearchtextbox"))
            
            search_input = page.locator("css=#twotabsearchtextbox")

            await search_input.fill(search_term)
            await search_input.press("Enter")

            await page.wait_for_load_state("load")

            search_results = page.locator('css=div[data-component-type="s-search-result"]')

            results: list[SearchResult] = []

            for search_result in await search_results.all():

                product_link = search_result.locator("a")

                link_url = await product_link.first.get_attribute("href")

                if link_url is not None:

                    is_sponsored = (
                        await search_result.locator(
                            "a.puis-sponsored-label-text"
                        ).count()
                        > 0
                    )

                    results.append(
                        {"product_link": link_url, "is_sponsored": is_sponsored}
                    )

            await browser.close()

            return results
    
    async def __wait_for_captcha(
        self, page: Page, element_waiter: Coroutine[Any, Any, ElementHandle | None]
    ) -> None:
        
        done, pending = await asyncio.wait(
            [
                element_waiter,
                self.__solve_captcha(page),
            ],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        has_captcha = False
        
        for task in done:
            result = await task
            
            if isinstance(result, ElementHandle):
                break
            
            has_captcha = True
        
        for task in pending:
            
            if has_captcha:
                if not task.done():
                    await task
                break
                
            task.cancel()

    
    async def __solve_captcha(
        self, page: Page
    ) -> None:
        
        catpcha_chars = await page.wait_for_selector("css=input#captchacharacters")
        
        amazon_captcha_image = page.locator("css=div.a-row img").first
        
        captcha = AmazonCaptcha.fromlink(await amazon_captcha_image.get_attribute("src"))
        
        solution = captcha.solve()
        
        if solution == "Not solved":
            raise ValueError("Failed to solve captcha")
        
        await catpcha_chars.fill(solution)
        
        send_button = page.get_by_role("button")
        
        await send_button.click()
        
        await page.wait_for_event("load")
        
    
    @activity.defn(name="amazon_brazil_scraping_extract_product_info")
    async def extract_product_info(
        self, product_link: str, geolocation: tuple[float, float]
    ) -> None:

        utc_now = datetime.now(timezone.utc)

        async with async_playwright() as p:

            browser = await p.chromium.launch(headless=self.headless)

            latitude, longitude = geolocation

            context = await browser.new_context(
                geolocation={"latitude": latitude, "longitude": longitude},
                permissions=["geolocation"],
            )

            context = await browser.new_context()

            page: Page = await context.new_page()

            await page.goto(urljoin(self.amazon_url, product_link))

            await page.wait_for_load_state("load")
            
            await self.__wait_for_captcha(page, page.wait_for_selector("span#productTitle"))

            activity.logger.info(f"Scraping product info from {product_link}")

            full_html = await page.content()

            product_html_strainer = SoupStrainer(is_tag_a_product_info)

            product_html = BeautifulSoup(
                full_html.encode().decode(),
                "lxml",
                parse_only=product_html_strainer,
            )

            try:
                
                product_info_doc = product_html_to_info_doc(product_html)
                
            except ValueError as e:
                
                activity.logger.error(f"Failed to extract product info: {e}")
                
                await browser.close()
                
                return

            asin = product_info_doc["details"].get("ASIN", None)
            
            # json_chunks = [json.dumps(chunk, ensure_ascii=False) for chunk in self.json_splitter.split_json(product_info_doc)]
            json_chunks = [json.dumps(product_info_doc, ensure_ascii=False)]
            
            metadata = {
                "product_link": product_link,
                "asin": asin,
                "country": "brazil",
                "geolocation": geolocation,
                "store": "amazon_brazil",
                "page": "product_details",
                "scraped_at": utc_now.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }

            vectors = self.openai_embeddings.embed_documents(json_chunks, self.embedding_size)

            for i in range(len(vectors)):
                
                vector = vectors[i]
                text = json_chunks[i]
                
                await self.elasticsearch_client.index(
                    index=f"{self.vector_index_alias}-{utc_now.strftime('%Y-%m-%V')}",
                    body={
                        "metadata": metadata,
                        "text": text,
                        "vector": vector,
                    },
                )


            await browser.close()
