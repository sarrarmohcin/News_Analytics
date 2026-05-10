from prefect import task, flow, unmapped
from prefect.task_runners import ThreadPoolTaskRunner
from datetime import datetime, timedelta
from prefect.logging import get_run_logger
from prefect.futures import wait
from prefect.states import State
from prefect.cache_policies import NO_CACHE
from prefect.schedules import Cron
import requests
import feedparser
import dateparser
import time
from typing import Any

from datetime import timedelta, datetime
from kafka import KafkaProducer
import json
import traceback
from elasticsearch import Elasticsearch



def cache_key(context, parameters):
    return "get_feeds_list_cache_key"

def get_published(entry):
    published = entry.get('published', None)
    if published:
        dt = dateparser.parse(published)
        if dt:
            article_published = int(dt.timestamp())
        else:
            # fallback to published_parsed
            pp = entry.get('published_parsed', None)
            if pp:
                article_published = int(time.mktime(pp))
            else:
                article_published = None
    else:
        # fallback to published_parsed
        pp = entry.get('published_parsed', None)
        if pp:
            article_published = int(time.mktime(pp))
        else:
            article_published = None
            
    if article_published is None:
        article_published = int(datetime.now().timestamp())
    
    return article_published
    
def get_content(entry):
    content = None
    if 'content' in entry and isinstance(entry['content'], list) and len(entry['content']) > 0:
        content = entry['content'][0].get('value', None)
    
    return content

def get_tags(entry):
    tags = []
    if 'tags' in entry:
        for tag in entry['tags']:
            term = tag.get('term') or tag.get('label')
            if term:
                tags.append(term)
                
    article_tags = ", ".join(tags) if tags else None
    
    return article_tags
     
def get_image(entry):
    image = None
    if 'media_content' in entry and len(entry['media_content']) > 0:
        image = entry['media_content'][0].get('url', None)
    elif 'media_thumbnail' in entry and len(entry['media_thumbnail']) > 0:
        image = entry['media_thumbnail'][0].get('url', None)
    elif 'enclosures' in entry and len(entry['enclosures']) > 0:
        image = entry['enclosures'][0].get('href', None)
    
    
    return image

@task(
    name="get_feeds_list",
    description="Getting list of feeds urls",
    task_run_name="get_feeds_list",
    timeout_seconds=60,
    retries=3,
    retry_delay_seconds=10,
    log_prints=False,
    cache_policy=NO_CACHE
    )
def get_feeds_list():
    logger = get_run_logger()
    try:
        es = Elasticsearch(
            "http://elasticsearch:9200",
            verify_certs=False
        )
        if es.ping():
            print("✓ Connected to Elasticsearch")
        else:
            raise Exception("✗ Failed to connect to Elasticsearch")
        
        # fetch feeds from elasticsearch
        response = es.search(
            index="sources",
            query={"match_all": {}},
            size=1000
        )
        feeds = [
            {**hit["_source"], "_id": hit["_id"]}
            for hit in response["hits"]["hits"]
        ]

        logger.info(f"Getting {len(feeds)} feeds urls")
        return feeds
    except Exception as e:
        logger.info(f"Failed getting feeds urls, {str(e)}")
        return None
        

@task(
    name="get_articles",
    description="Getting articles from rss url",
    task_run_name="get_articles",
    timeout_seconds=120,
    retries=3,
    retry_delay_seconds=15,
    log_prints=False,
    cache_policy=NO_CACHE
    )
def get_articles(feed, producer):
    logger = get_run_logger()
    
    ACCEPT_HEADER = (
        "application/atom+xml,"
        "application/rdf+xml,"
        "application/rss+xml,"
        "application/x-netcdf,"
        "application/xml;q=0.9,"
        "text/xml;q=0.2,"
        "*/*;q=0.1"
    )
    
    headers = {
        "Accept": ACCEPT_HEADER,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",  
    }
    
    try:
        
        response = requests.get(feed['url'], headers=headers, timeout=60)
        response.raise_for_status()
        rss_response = feedparser.parse(response.content)
        
        entries = rss_response.get('entries', [])
        if not entries:
            raise ValueError("No entries found in the feed")
        
                
        articles_count = 0
        for entry in entries:
            title = entry.get('title', None)
            link = entry.get('link', None)
            published = get_published(entry)
            summary = entry.get('summary', None)
            content = get_content(entry)
            tags = get_tags(entry)
            image = get_image(entry)
            author = entry.get('author', None)
            
            article = {
                'source_id': feed['_id'],
                'source_name': feed['name'],
                'title': title,
                'link': link,
                'published': published,
                'summary': summary,
                'content': content,
                'tags': tags,
                'image': image,
                'author': author,
            }
            
            # push to kafka
            future = producer.send("news", value=article)

            # Wait for send confirmation
            result = future.get(timeout=10)
            print(f"Message sent: {result}")
            articles_count += 1

        logger.info(f"Get {articles_count} articles from feed {feed['name']}")
        return articles_count
    
    except Exception as e:
        traceback.print_exc()
        logger.info(f"Failed getting articles, {str(e)}")
        return None


@flow(
    name="rss_scraper",
    description="Getting articles from RSS feeds",
    flow_run_name=lambda: f"rss_scraper_{datetime.now().strftime('%Y%m%d-%H%M%S')}",
    retries=0,
    task_runner=ThreadPoolTaskRunner(max_workers=10),
    log_prints=False
    )
def rss_scraper():
    # get logger
    logger = get_run_logger()
    
    # connect to kafka
    producer = KafkaProducer(
        bootstrap_servers='kafka:9092',  # Kafka broker address
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),  # Serialize JSON
    )
    
    # run get_feeds_list task
    feeds = get_feeds_list()
    if feeds is None:
        return None
    
    
    # run get_articles task for each feed
    
    # Submit all tasks and return the futures 
    futures = get_articles.map(feeds, unmapped(producer)) 
    
    # Wait for all futures to complete concurrently 
    done, not_done = wait(futures) 
    
    # Check each future's state 
    successful: list[Any] = [] 
    failed: list[State] = [] 
    for future in done: 
        if future.state.is_completed(): 
            successful.append(future.result()) 
        else: 
            failed.append(future.state)
    
    total_articles = sum(r or 0 for r in successful)
    total_feeds = len([r for r in successful if r is not None])
    failed_feeds = len([r for r in successful if r is None])
    
    logger.info(f"✓ Processed {total_feeds} feed successfully")
    logger.info(f"✗ Failed to process {failed_feeds} feeds")
    
    logger.info(f"Total articles fetched: {total_articles}")
    
    
    # Close producer
    producer.close()
        
        
if __name__ == "__main__":
    rss_scraper.from_source(
        source=".",  # Example: Git repository
        entrypoint="newsFeed.py:rss_scraper"
    ).deploy(
        name="my-deployment",
        work_pool_name="local-pool",
        schedule=Cron("*/10 * * * *")
    )