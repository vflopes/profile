import asyncio

from temporalio.worker import Worker

from container import Container

from workflows import ListAmazonBrazilProducts

from activities import AmazonBrazilScraping

import logging

async def main():

    logging.basicConfig(level=logging.INFO)

    container = Container()

    container.config.from_yaml("config.yaml")

    await container.init_resources()

    temporal_client = await container.temporal_client()

    task_queue = container.config.temporal.task_queue()

    amazon_brazil_scraping = AmazonBrazilScraping(
        headless=container.config.amazon.brazil.headless(),
    )

    worker = Worker(
        client=temporal_client,
        task_queue=task_queue,
        workflows=[ListAmazonBrazilProducts],
        activities=[
            amazon_brazil_scraping.search,
            amazon_brazil_scraping.get_product_info,
        ],
    )

    await worker.run()

    await container.shutdown_resources()

if __name__ == "__main__":
    asyncio.run(main())