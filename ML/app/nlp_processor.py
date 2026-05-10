from keybert import KeyBERT
from transformers import pipeline
import spacy

# ------------ Load NLP models --------------
kw_model = KeyBERT("sentence-transformers/all-MiniLM-L6-v2")
sentiment_model = pipeline("sentiment-analysis", model="distilbert/distilbert-base-uncased-finetuned-sst-2-english")
nlp = spacy.load("en_core_web_sm")

# ------------ NLP Pipeline Function --------------
def enrich_article(article):
    title = article.get("title", None)
    content = article.get("content", None)
    summary = article.get("summary", None)
    
    text = content or summary or title
    
    # Keywords
    keywords = [k[0] for k in kw_model.extract_keywords(text, top_n=5)]


    # Sentiment
    sentiment_result = sentiment_model(text[:500])[0]
    sentiment = sentiment_result["score"] if sentiment_result["label"] == "POSITIVE" else -sentiment_result["score"]


    # Entities (spaCy)
    entities_types = ['PERSON', 'NORP', 'ORG', 'GPE', 'LOC', 'EVENT', 'PRODUCT', 'WORK_OF_ART']
    doc = nlp(text)
    filtered_entities = []
    for ent in doc.ents:
        if ent.label_ in entities_types:
            filtered_entities.append(ent.text)
        
    return {
        "keywords": keywords,
        "sentiment": sentiment_result["label"],
        "entities": list(set(filtered_entities))
    }
