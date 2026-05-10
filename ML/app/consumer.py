from kafka import KafkaConsumer
import json
import time
from nlp_processor import enrich_article
from elasticsearch import Elasticsearch

import hashlib

def get_article_id(article):
    link = article.get("link", None)
    if link is None:
        return None
    return hashlib.md5(link.encode()).hexdigest()


error_count = 0
while True:
    
    try:
        # connect to Kafka
        print("Connecting to Kafka...")
        consumer = KafkaConsumer(
            "news",
            bootstrap_servers="kafka:9092",
            auto_offset_reset="earliest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            enable_auto_commit=False,
            group_id="news-consumer"
        )
        if consumer.bootstrap_connected():
            print("✓ Connected to Kafka successfully")
        else:
            raise Exception("✗ Failed to connect to Kafka")
            
        # connect to Elasticsearch
        print("Connecting to Elasticsearch...")
        es = Elasticsearch(
            "http://elasticsearch:9200",
            verify_certs=False
        )
        if es.ping():
            print("✓ Connected to Elasticsearch")
        else:
            raise Exception("✗ Failed to connect to Elasticsearch")
        
        print('fetching messages from kafka...')
        for msg in consumer:
            try:
                print(f"Processing message at offset {msg.offset}")
                # get article from message
                article = msg.value
                
                # create unique ID for the article
                article_id = get_article_id(article)
                if article_id is None:
                    print("Skipping article without link")
                    continue
                
                # enrich article using NLP processor
                enriched = enrich_article(article)
                
                # merge original article with enriched data
                article.update(enriched)
                
                # Index the enriched article into Elasticsearch
                try:
                    es.index(index="news", id=article_id, body=article, op_type="create")
                    print(f"Indexed article with ID: {article_id}")
                except Exception as e:
                    print(f"Failed to index article (might be duplicate), {str(e)}")
                    pass
                
                # Commit offsets after processing batch
                consumer.commit()
                
            except Exception as e:
                print("Error processing message:", str(e))
                
                # Sleep for 2 minutes
                print("Sleeping for 15 seconds...")
                time.sleep(15) 
                continue

    except Exception as e:
        print(f"FATAL error: {e}")
        
        error_count += 1
        if error_count >= 5:
            print("Exceeded maximum retry attempts. Exiting.")
            break
        
        print("Retrying connection in 10 seconds...")
        time.sleep(10)
        
        
