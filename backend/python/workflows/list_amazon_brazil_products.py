import asyncio

from temporalio import workflow

from activities import AmazonBrazilScraping

from datetime import timedelta

@workflow.defn
class ListAmazonBrazilProducts:

    @workflow.run
    async def run(self, search_expression: str, geolocation: tuple[float,float], max_pages: int = 1, max_parallel_count: int = 2) -> None:

        for page in range(1, max_pages + 1):
            
            found_products = await workflow.execute_activity(
                activity=AmazonBrazilScraping.search,
                start_to_close_timeout=timedelta(seconds=15),
                args=[search_expression, page, geolocation],
            )

            sponsored_count = 0

            for product in found_products:

                if product["is_sponsored"]:
                    sponsored_count += 1

            if sponsored_count == len(found_products):
                workflow.logger.info("All products on page %d are sponsored", page)
                break
            
            parallel_activities = []
            
            products_info = []

            for product in found_products:
                    
                    parallel_activities.append(
                        workflow.execute_activity(
                            activity=AmazonBrazilScraping.get_product_info,
                            start_to_close_timeout=timedelta(seconds=15),
                            args=[product["product_link"], geolocation],
                        )
                    )

                    if len(parallel_activities) == max_parallel_count:
                        products_info = await asyncio.gather(*parallel_activities)
                        parallel_activities = []

                        return products_info

            if len(parallel_activities) > 0:
                products_info = await asyncio.gather(*parallel_activities)
            