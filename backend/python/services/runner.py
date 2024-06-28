import asyncio

from container import Container
from services import ProductsRagService

async def main():

    container = Container()

    container.config.from_yaml("config.yaml")

    await container.init_resources()

    products_rag = ProductsRagService(
        elasticsearch_url=container.config.elasticsearch.hosts()[0],
        openai_embeddings=container.openai_embeddings(),
        chat_openai=container.chat_openai(),
        vector_index_alias="products-vector-brazil-amazon-2024-05-18",
    )

    print(products_rag.rag_chain.invoke("Qual ar condicionado é ideal para um quarto de 3 metros de largura por 5 metros de comprimento?"))
    


if __name__ == "__main__":
    asyncio.run(main())