#!/bin/bash

/etc/confluent/docker/run
# /etc/confluent/docker/run &

# CONNECT_LOCALHOST="http://localhost:8083"

# echo "Waiting for Kafka Connect availability..."
# while : ; do
#   curl -s $CONNECT_LOCALHOST/connectors > /dev/null
#   if [ $? -eq 0 ]; then
#     break
#   fi
#   echo "Kafka Connect is not available yet. Waiting 5 seconds to retry..."
#   sleep 5
# done


# echo "Registering Elasticsearch connector..."
# curl -X POST -H "Content-Type: application/json" --data @/config/"$CONNECTOR_NAME"-connector-config.json $CONNECT_LOCALHOST/connectors