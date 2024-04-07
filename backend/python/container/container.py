from dependency_injector import containers, providers

from temporalio.client import Client

class Container(containers.DeclarativeContainer):

    config = providers.Configuration()
    
    temporal_client = providers.Resource(
        Client.connect,
        target_host = config.temporal.server_address,
        namespace = config.temporal.namespace,
    )
    