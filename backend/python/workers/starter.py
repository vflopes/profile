import asyncio

from container import Container

from temporalio.client import Client

from temporalio.common import WorkflowIDReusePolicy

from workflows import ListAmazonBrazilProducts

async def main():

    container = Container()

    container.config.from_yaml("config.yaml")

    await container.init_resources()

    temporal_client: Client = await container.temporal_client()

    task_queue = container.config.temporal.task_queue()

    await temporal_client.execute_workflow(
        ListAmazonBrazilProducts.run,
        id="search_on_amazon",
        id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
        task_queue=task_queue,
        args=(
            "ar condicionado",
            (-23.541128, -46.641581),
            1,
        ),
    )

    await container.shutdown_resources()

if __name__ == "__main__":
    asyncio.run(main())