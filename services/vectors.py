"""Revision-bound dense embeddings; provider errors never expose credentials."""
import hashlib
import json
import math
from pathlib import Path

MODEL='gemini-embedding-001'
DIMENSIONS=768


def fingerprint(data):
    raw=json.dumps([data.get('schema_version'),data['document']['sha256'],[(c['id'],c['text'],c.get('heading_path',[])) for c in data['chunks']
                    if c['curriculum_status']=='primary']],ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def unit(vector):
    v=[float(x) for x in vector];norm=math.sqrt(sum(x*x for x in v))
    if not v or not math.isfinite(norm) or norm==0:raise ValueError('Invalid embedding vector')
    return [x/norm for x in v]


def embedding_text(chunk):
    return ' > '.join(chunk.get('heading_path',[]))+'\n\n'+chunk['text']


def build_index(data,*,embed):
    chunks=[c for c in data['chunks'] if c['curriculum_status']=='primary']
    rows=embed([embedding_text(c) for c in chunks],'RETRIEVAL_DOCUMENT')
    if len(rows)!=len(chunks) or not rows:raise ValueError('Incomplete embedding index')
    rows=[unit(v) for v in rows];dimensions=len(rows[0])
    if any(len(v)!=dimensions for v in rows):raise ValueError('Mixed embedding dimensions')
    return dict(model=MODEL,revision=fingerprint(data),dimensions=dimensions,
                rows=[dict(id=c['id'],vector=v) for c,v in zip(chunks,rows)])


def search_index(query,data,index,*,embed):
    expected=[c['id'] for c in data['chunks'] if c['curriculum_status']=='primary']
    if (index['revision']!=fingerprint(data) or index['model']!=MODEL
        or [r['id'] for r in index['rows']]!=expected):raise ValueError('Stale or incomplete vector index')
    response=embed([query],'RETRIEVAL_QUERY')
    if len(response)!=1:raise ValueError('Invalid query embedding')
    q=unit(response[0]);scores={}
    if len(q)!=index['dimensions']:raise ValueError('Query dimensions differ')
    for row in index['rows']:
        v=unit(row['vector'])
        if len(v)!=len(q):raise ValueError('Stored dimensions differ')
        scores[row['id']]=sum(a*b for a,b in zip(q,v))
    return scores


def provider(api_key):
    def embed(texts,task):
        from google import genai
        from google.genai import types
        try:
            with genai.Client(api_key=api_key,http_options=types.HttpOptions(timeout=30000)) as client:
                result=client.models.embed_content(model=MODEL,contents=texts,
                    config=types.EmbedContentConfig(task_type=task,output_dimensionality=DIMENSIONS))
                rows=[e.values for e in result.embeddings or []]
                if len(rows)!=len(texts) or any(len(v)!=DIMENSIONS for v in rows):
                    raise ValueError('Provider batch incomplete')
                if any(getattr(getattr(e,'statistics',None),'truncated',False) for e in result.embeddings):
                    raise ValueError('Provider truncated evidence')
                for row in rows:unit(row)
                return rows
        except Exception as exc:
            status=getattr(exc,'code',None)
            raise ValueError(f'Embedding provider unavailable (status {status if type(status) is int else "unknown"}); offline search remains available') from None
    return embed
