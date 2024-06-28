docker build -t kafka-connect-elasticsearch:latest -f devops/container/Containerfile.connect.elasticsearch .

docker build -t kafka-connect-gcs:latest -f devops/container/Containerfile.connect.gcs .

docker compose -f devops/container/docker-compose.yaml up

docker compose -f devops/container/docker-compose.yaml exec kafka kafka-topics --create --topic product-info --partitions 2 --replication-factor 1 --bootstrap-server kafka:9092