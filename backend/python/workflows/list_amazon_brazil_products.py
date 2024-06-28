import asyncio

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
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

            for product in found_products:
                
                if "bestsellers" in product["product_link"]:
                    continue
                
                parallel_activities.append(
                    workflow.execute_activity(
                        activity=AmazonBrazilScraping.extract_product_info,
                        start_to_close_timeout=timedelta(seconds=15),
                        args=[product["product_link"], geolocation],
                    )
                )

                if len(parallel_activities) == max_parallel_count:
                    await asyncio.gather(*parallel_activities)
                    parallel_activities = []
            
            if len(parallel_activities) > 0:
                await asyncio.gather(*parallel_activities)
            