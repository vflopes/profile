from langchain_elasticsearch import ElasticsearchRetriever
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from typing import Dict

template = """Você é um assistente de compra. Seu objetivo é ajudar os clientes a fazerem a escolha ideal de produtos para optar pela opção ideal na relação entre custo e benefício. Para isso você terá a sua disponibilidade funções de pesquisa e busca de produtos e suas características em diferentes ecommerce.

Caso o cliente queira conversar com você sobre qualquer outra coisa, se comporte como vendedor. Utilize isso para levar o cliente de volta à decisão de compra. Nunca fale sobre outros assuntos que não estejam ligados à sua função como assistente de compra.

Apresente ao cliente sempre comparações e escolhas justas de produtos, informando de forma efetiva suas sugestões e perguntando de forma clara sobre o que o cliente gostaria de considerar na compra.

Não sobrecarregue os clientes, as respostas e perguntas tem que ser objetivas, curtas e diretas ao ponto. Não faça múltiplas perguntas de uma só vez, fracione para manter o cliente engajado. Utilize as informações abaixo para ajudar o cliente a tomar a melhor decisão.

{context}

Questão: {question}

Resposta:"""


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


class ProductsRagService:

    def vector_query(self, search_query: str) -> Dict:

        vector = self.openai_embeddings.embed_query(search_query)

        return {
            "knn": {
                "field": "vector",
                "query_vector": vector,
                "k": 5,
                "num_candidates": 10,
            }
        }

    def __init__(
        self,
        elasticsearch_url: str,
        openai_embeddings: OpenAIEmbeddings,
        chat_openai: ChatOpenAI,
        vector_index_alias: str = "products-vector-brazil-amazon",
    ) -> None:

        self.openai_embeddings = openai_embeddings

        self.chat_openai = chat_openai

        self.vector_index_alias = vector_index_alias

        self.vector_retriever = ElasticsearchRetriever.from_es_params(
            index_name=self.vector_index_alias,
            body_func=self.vector_query,
            content_field="text",
            url=elasticsearch_url,
        )

        custom_rag_prompt = PromptTemplate.from_template(template)

        self.rag_chain = (
            {
                "context": self.vector_retriever | format_docs,
                "question": RunnablePassthrough(),
            }
            | custom_rag_prompt
            | self.chat_openai
            | StrOutputParser()
        )
