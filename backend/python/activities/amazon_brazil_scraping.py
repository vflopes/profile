import urllib

from temporalio import activity

from playwright.async_api import async_playwright, Page

from typing import TypedDict

from urllib.parse import urljoin

class SearchResult(TypedDict):

    product_link: str
    is_sponsored: bool


class ProductImage(TypedDict):

    thumbnail_url: str
    image_url: str

class GetProductInfoResult(TypedDict):

    product_title: str
    price_symbol: str
    product_price: float
    product_description: str
    product_attributes: dict[str, str]
    product_images: list[ProductImage]


class AmazonBrazilScraping:

    amazon_url: str = "https://www.amazon.com.br"

    search_input_xpath: str = 'xpath=//*[@id="twotabsearchtextbox"]'
    search_result_css = 'css=div[data-component-type="s-search-result"]'

    def __init__(self, headless: bool = False):
        self.headless = headless

    @activity.defn(name="amazon_brazil_scraping_search")
    async def search(self, search_term: str, page: int, geolocation: tuple[float, float]) -> list[SearchResult]:
        async with async_playwright() as p:

            browser = await p.chromium.launch(headless=self.headless)

            latitude, longitude = geolocation

            context = await browser.new_context(
                geolocation={"latitude": latitude, "longitude": longitude},
                permissions=["geolocation"]
            )

            page: Page = await context.new_page()

            await page.goto(self.amazon_url)

            await page.fill(self.search_input_xpath, search_term)
            await page.press(self.search_input_xpath, "Enter")

            await page.wait_for_load_state("load")

            search_results = page.locator(self.search_result_css)

            results: list[SearchResult] = []

            for search_result in await search_results.all():

                product_link = search_result.locator("a")

                link_url = await product_link.first.get_attribute("href")

                if link_url is not None:
                    
                    is_sponsored = await search_result.locator("a.puis-sponsored-label-text").count() > 0
                    
                    results.append({
                        "product_link": link_url,
                        "is_sponsored": is_sponsored
                    })

            await browser.close()

            return results


    @activity.defn(name="amazon_brazil_scraping_get_product_info")
    async def get_product_info(self, product_link: str, geolocation: tuple[float, float]) -> GetProductInfoResult:
        async with async_playwright() as p:

            browser = await p.chromium.launch(headless=self.headless)

            latitude, longitude = geolocation

            context = await browser.new_context(
                geolocation={"latitude": latitude, "longitude": longitude},
                permissions=["geolocation"]
            )

            context = await browser.new_context()

            page: Page = await context.new_page()

            await page.goto(urljoin(self.amazon_url, product_link))

            await page.wait_for_load_state("load")

            product_info: GetProductInfoResult = await page.evaluate(
                """
                () => {
                    const productTitle = document.querySelector("h1#title span").innerText;
                    const priceToPay = document.querySelector("span.priceToPay");

                    const priceSymbol = priceToPay.querySelector("span.a-price-symbol").innerText;
                    const priceWhole = priceToPay.querySelector("span.a-price-whole").innerText.replaceAll(".", "");
                    const priceFraction = priceToPay.querySelector("span.a-price-fraction").innerText;

                    const productPrice = parseFloat(`${priceWhole}.${priceFraction}`);

                    const productDescription = document.querySelector("div#productDescription p span").innerText;

                    const productDetailTables = document.querySelectorAll("table.prodDetTable");

                    const productAttributes = {};

                    for (let table of productDetailTables) {
                    
                        const rows = table.querySelectorAll("tr");

                        for (let row of rows) {
                            const attributeName = row.querySelector("th").innerText;
                            const attributeValue = row.querySelector("td").innerText;

                            productAttributes[attributeName] = attributeValue;
                        }

                    }

                    return {
                        "product_title": productTitle,
                        "price_symbol": priceSymbol,
                        "product_price": productPrice,
                        "product_description": productDescription,
                        "product_attributes": productAttributes,
                        "product_images": [],
                    }
                }
                """
            )

            product_info["product_attributes"] = {k: v.strip('\u200e') for k, v in product_info["product_attributes"].items()}

            product_image = page.locator("css=div#imgTagWrapperId img")

            thumbnails = await page.locator("css=li.imageThumbnail").all()

            for thumbnail in thumbnails:

                await thumbnail.click()

                thumbnail_url = await thumbnail.locator("img").first.get_attribute("src")

                if thumbnail_url is not None:
                    product_info["product_images"].append({
                        "thumbnail_url": thumbnail_url,
                        "image_url": await product_image.first.get_attribute("src")
                    })
                    break

            all_reviews_link = page.locator("a.see-all-reviews-link-foot")

            if await all_reviews_link.count() > 0:

                await all_reviews_link.first.click()

                await page.wait_for_load_state("load")

                reviews = await page.locator("css=div.review").all()

            await browser.close()

            return product_info