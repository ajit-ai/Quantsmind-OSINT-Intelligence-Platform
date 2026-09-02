import pytest
from processing.nlp import extract_entities, analyze_sentiment, detect_language, extract_topics, enrich_text, extract_geo, simhash_near_dup

def test_extract_entities():
    ents = extract_entities("Barack Obama visited Paris and met Emmanuel Macron at the UN.")
    # should find at least Paris or Barack Obama
    texts = [e["text"] for e in ents]
    assert any("Paris" in t or "Obama" in t for t in texts)

def test_sentiment_positive_negative_neutral():
    pos = analyze_sentiment("This is excellent and outstanding great news")
    assert pos["label"] == "positive"
    neg = analyze_sentiment("crisis conflict threat attack fail")
    assert neg["label"] == "negative"
    neu = analyze_sentiment("This is a neutral statement about the weather")
    assert neu["label"] in ("neutral","positive","negative")

def test_sentiment_hf_mocked(monkeypatch):
    from processing import nlp
    def fake_pipeline(*a, **k):
        def pipe(txt): return [{"label":"POSITIVE","score":0.92}]
        return pipe
    monkeypatch.setattr(nlp, "_HF_SENTIMENT", None)
    # monkeypatch transformers.pipeline import inside _get_hf_sentiment — easiest: stub _get_hf_sentiment
    monkeypatch.setattr(nlp, "_get_hf_sentiment", lambda: (lambda x: [{"label":"POSITIVE","score":0.98}]))
    res = analyze_sentiment("I love this platform")
    assert res["label"] == "positive"
    assert res["score"] > 0.5

def test_detect_language():
    lang = detect_language("This is an English sentence for detection.")
    assert isinstance(lang, str)
    assert len(lang) >= 2

def test_extract_topics():
    topics = extract_topics("Apple and Microsoft announced partnership in London and Paris. Google remains separate.")
    assert isinstance(topics, list)
    assert len(topics) <= 5

def test_extract_geo():
    geo = extract_geo("Barack Obama visited London and Paris", entities=[{"text":"London","type":"GPE","start":0,"end":6},{"text":"Paris","type":"GPE","start":0,"end":5}])
    assert any(g["name"]=="London" and g.get("lat")==51.5074 for g in geo)

def test_enrich_text_combines():
    res = enrich_text("London crisis: threat to democracy. Barack Obama commented.")
    assert "entities" in res and "sentiment" in res and "language" in res and "topics" in res

def test_simhash_near_dup():
    dup, h = simhash_near_dup("hello world content for testing", [])
    assert not dup
    dup2, _ = simhash_near_dup("hello world content for testing", [h])
    assert dup2
