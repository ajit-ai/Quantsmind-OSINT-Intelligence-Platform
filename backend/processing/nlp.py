import re
try:
    import spacy
    _nlp = None
    def get_nlp():
        global _nlp
        if _nlp is None:
            try: _nlp = spacy.load("en_core_web_sm")
            except: _nlp = spacy.blank("en")
        return _nlp
except: get_nlp = lambda: None

try:
    from langdetect import detect
except:
    def detect(x): return "en"

SENTIMENT_LEXICON = {"good":1,"great":1,"positive":1,"excellent":1,"bad":-1,"negative":-1,"crisis":-1,"conflict":-1,"threat":-1}

def analyze_sentiment(text: str):
    score = sum(SENTIMENT_LEXICON.get(w.lower(),0) for w in text.split())
    if score > 1: return {"label":"positive","score": min(0.99, 0.6+score*0.05)}
    if score < -1: return {"label":"negative","score": min(0.99, 0.6+abs(score)*0.05)}
    return {"label":"neutral","score":0.5}

def extract_entities(text: str):
    nlp = get_nlp()
    if nlp is None: return []
    doc = nlp(text[:5000])
    return [{"text": ent.text, "type": ent.label_, "start": ent.start_char, "end": ent.end_char} for ent in doc.ents]

def detect_language(text: str):
    try: return detect(text[:1000])
    except: return "en"

def extract_topics(text: str):
    # keyword-based fallback; replace with BERTopic in production
    keywords = re.findall(r"\b[A-Z][a-z]+\b", text)
    topics = list({k.lower() for k in keywords})[:5]
    return topics

def enrich_text(text: str):
    return {
        "entities": extract_entities(text),
        "sentiment": analyze_sentiment(text),
        "language": detect_language(text),
        "topics": extract_topics(text),
    }
