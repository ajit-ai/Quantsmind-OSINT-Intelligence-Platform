import re
import hashlib

# --- spaCy NER with lazy load + fallback to blank ---
try:
    import spacy
    _nlp = None
    def get_nlp():
        global _nlp
        if _nlp is None:
            try:
                _nlp = spacy.load("en_core_web_sm")
            except Exception as e:
                print(f"[nlp] spacy model missing, using blank: {e}")
                _nlp = spacy.blank("en")
                # add sentencizer for pipeline completeness
                if "sentencizer" not in _nlp.pipe_names:
                    _nlp.add_pipe("sentencizer")
        return _nlp
except Exception:
    get_nlp = lambda: None

# --- language detection ---
try:
    from langdetect import detect as _detect
    def detect_lang(x):
        try:
            return _detect(x[:2000])
        except Exception:
            return "en"
except Exception:
    def detect_lang(x): return "en"

# --- sentiment: try HF transformers pipeline, fallback to lexicon ---
_HF_SENTIMENT = None
def _get_hf_sentiment():
    global _HF_SENTIMENT
    if _HF_SENTIMENT is not None:
        return _HF_SENTIMENT
    try:
        from transformers import pipeline
        # small, CPU-friendly model; lazy — downloaded on first use
        _HF_SENTIMENT = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english", tokenizer="distilbert-base-uncased-finetuned-sst-2-english", framework="pt")
        print("[nlp] HF sentiment pipeline loaded")
    except Exception as e:
        print(f"[nlp] HF not available, lexicon fallback: {e}")
        _HF_SENTIMENT = False
    return _HF_SENTIMENT

LEXICON = {"good":1,"great":1,"positive":1,"excellent":2,"outstanding":2,"bad":-1,"negative":-1,"crisis":-2,"conflict":-2,"threat":-2,"attack":-2,"risk":-1,"fail":-1}

def analyze_sentiment(text: str):
    txt = (text or "")[:2000].strip()
    if not txt:
        return {"label":"neutral","score":0.5}
    pipe = _get_hf_sentiment()
    if pipe:
        try:
            res = pipe(txt[:512])
            # res: [{"label":"POSITIVE"/"NEGATIVE","score":0.98}]
            label = (res[0]["label"] or "").lower()
            score = float(res[0].get("score",0.5))
            if "pos" in label: return {"label":"positive","score": score}
            if "neg" in label: return {"label":"negative","score": score}
            return {"label": label, "score": score}
        except Exception as e:
            print(f"[sentiment] HF infer failed, lexicon: {e}")
    # lexicon fallback (deterministic, fast)
    score = sum(LEXICON.get(w.lower().strip(".,!?:;()"),0) for w in txt.split())
    if score >= 2: return {"label":"positive","score": min(0.99, 0.6+score*0.04)}
    if score <= -2: return {"label":"negative","score": min(0.99, 0.6+abs(score)*0.04)}
    return {"label":"neutral","score":0.5}

def extract_entities(text: str):
    nlp = get_nlp()
    if nlp is None: return []
    doc = nlp((text or "")[:5000])
    ents = []
    for ent in doc.ents:
        # filter noisy types
        if ent.label_ in ("PERSON","ORG","GPE","LOC","EVENT","PRODUCT","NORP","FAC"):
            ents.append({"text": ent.text.strip(), "type": ent.label_, "start": ent.start_char, "end": ent.end_char})
    # de-duplicate by (text,type)
    seen = set()
    uniq = []
    for e in ents:
        k=(e["text"].lower(), e["type"])
        if k not in seen:
            seen.add(k); uniq.append(e)
    return uniq[:30]

def detect_language(text: str):
    return detect_lang(text or "")

# --- topic: try BERTopic, fallback to KeyBERT-style keyword extraction ---
_BERTOPIC = None
def _get_bertopic():
    global _BERTOPIC
    if _BERTOPIC is not None: return _BERTOPIC
    try:
        from bertopic import BERTopic
        _BERTOPIC = BERTopic(verbose=False, calculate_probabilities=False)
        print("[nlp] BERTopic available")
    except Exception as e:
        print(f"[nlp] BERTopic not available: {e}")
        _BERTOPIC = False
    return _BERTOPIC

def extract_topics(text: str):
    txt = (text or "").strip()
    if not txt: return []
    # Try BERTopic (requires embeddings; may be heavy so we gate behind env)
    import os
    if os.getenv("ENABLE_BERTOPIC","0") == "1":
        bt = _get_bertopic()
        if bt:
            try:
                topics, _ = bt.fit_transform([txt])
                # BERTopic returns -1 for outliers
                if topics and topics[0] != -1:
                    info = bt.get_topic_info()
                    if info is not None and not info.empty:
                        top = info.iloc[0]
                        words = [w for w,_ in bt.get_topic(top["Topic"])[:5]] if "Topic" in top else []
                        if words: return words[:5]
            except Exception as e:
                print(f"[topic] BERTopic failed: {e}")
    # Lightweight fallback: capitalized phrases + noun chunks
    keywords = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b", txt)
    # enrich with noun chunks from spaCy
    try:
        nlp = get_nlp()
        if nlp:
            doc = nlp(txt[:2000])
            keywords += [chunk.text for chunk in doc.noun_chunks if len(chunk.text.split())<=3]
    except Exception:
        pass
    # normalize, dedup, filter stopwords
    stop = {"the","and","for","with","from","this","that","will","have","has","been","were","are"}
    topics = []
    seen=set()
    for k in keywords:
        nk = k.strip().lower()
        if len(nk)<3 or nk in stop or nk in seen: continue
        seen.add(nk); topics.append(nk)
        if len(topics)>=5: break
    return topics

# --- geo: lightweight location extraction from entities ---
def extract_geo(text: str, entities=None):
    # Use GPE/LOC entities + simple lat/lon placeholder map
    # Production: replace with Mordecai/geonames or Nominatim
    if not entities:
        entities = extract_entities(text)
    locs=[]
    for e in entities:
        if e["type"] in ("GPE","LOC","FAC"):
            # naive demo coords for common cities — real geocoder would resolve
            demo_coords = {
                "london": (51.5074,-0.1278), "new york": (40.7128,-74.0060), "delhi": (28.6139,77.2090),
                "mumbai": (19.076,72.8777), "beijing": (39.9042,116.4074), "paris": (48.8566,2.3522),
                "moscow": (55.7558,37.6173), "dubai": (25.2048,55.2708), "singapore": (1.3521,103.8198),
            }
            key = e["text"].lower()
            if key in demo_coords:
                lat, lon = demo_coords[key]
                locs.append({"name": e["text"], "type": e["type"], "lat": lat, "lon": lon})
            else:
                locs.append({"name": e["text"], "type": e["type"]})
    return locs

def enrich_text(text: str):
    return {
        "entities": extract_entities(text),
        "sentiment": analyze_sentiment(text),
        "language": detect_language(text),
        "topics": extract_topics(text),
        "geo_locations": extract_geo(text),
    }

def simhash_near_dup(text: str, existing_hashes, threshold=3):
    # simple Hamming distance on sha256 prefix for demo; production uses simhash lib
    h = hashlib.sha256((text or "").encode()[:4000]).hexdigest()
    # compare first 16 hex chars as proxy
    for eh in existing_hashes:
        # count differing chars
        diff = sum(a!=b for a,b in zip(h[:16], eh[:16] if isinstance(eh,str) else ""))
        if diff <= threshold:
            return True, h
    return False, h
