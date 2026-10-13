"""Whole-evidence budgeting. No mid-sentence truncation."""
import json


def token_count(text):
    import tiktoken
    return len(tiktoken.get_encoding('cl100k_base').encode(text,disallowed_special=()))


def evidence_text(chunk):
    return json.dumps({'id':chunk['id'],'page':chunk.get('page'),'text':chunk['text']},ensure_ascii=False)


def select_evidence(chunks,budget=1250,count_tokens=token_count):
    selected=[]; used=0
    for chunk in chunks:
        cost=count_tokens(evidence_text(chunk))
        if used+cost<=budget:
            selected.append(chunk);used+=cost
    return selected
