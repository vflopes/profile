```
PUT _index_template/products-vector
{
  "index_patterns": ["products-vector-*"],
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 1
    },
    "mappings": {
      "properties": {
        "vector": {
          "type": "dense_vector",
          "dims": 1536
        },
        "text": {
          "type": "text"
        },
        "metadata": {
          "properties": {
            "product_link": {
              "type": "text"
            },
            "country": {
              "type": "keyword"
            },
            "asin": {
              "type": "keyword"
            },
            "geolocation": {
              "type": "geo_point"
            },
            "store": {
              "type": "keyword"
            },
            "page": {
              "type": "keyword"
            }
          }
        }
      }
    }
  }
}
```