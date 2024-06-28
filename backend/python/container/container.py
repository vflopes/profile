# import json

from dependency_injector import containers, providers

from temporalio.client import Client

from elasticsearch import AsyncElasticsearch
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

# from kafka import KafkaProducer
# from kafka.partitioner import DefaultPartitioner

class Container(containers.DeclarativeContainer):

    config = providers.Configuration()
    
    temporal_client = providers.Resource(
        Client.connect,
        target_host = config.temporal.server_address,
        namespace = config.temporal.namespace,
    )
    
    elasticsearch_async_client = providers.Resource(
        AsyncElasticsearch,
        hosts = config.elasticsearch.hosts,
    )
    
    openai_embeddings = providers.Resource(
        OpenAIEmbeddings,
        api_key = config.openai.api_key,
        model = config.openai.embedding_model,
    )
    
    chat_openai = providers.Resource(
        ChatOpenAI,
        api_key = config.openai.api_key,
        model = config.openai.chat_model,
    )
    
    # kafka_producer = providers.Resource(
    #     KafkaProducer,
    #     bootstrap_servers = config.kafka.bootstrap_servers,
    #     partitioner = DefaultPartitioner(),
    #     value_serializer = lambda v: json.dumps(v).encode('utf-8'),
    # )