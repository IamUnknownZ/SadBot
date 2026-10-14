"""Revision-bound dense embeddings; provider errors never expose credentials."""
import hashlib
import json
import math
import sqlite3
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


def _cached_query_vector(query,index,embed,cache_path):
    """Return a revision-bound vector while storing only a hash of the query."""
    if cache_path is None:
        response=embed([query],'RETRIEVAL_QUERY')
        return response[0] if len(response)==1 else None
    path=Path(cache_path);path.parent.mkdir(parents=True,exist_ok=True)
    key=hashlib.sha256(query.strip().casefold().encode()).hexdigest()
    with sqlite3.connect(path,timeout=10) as db:
        db.execute('CREATE TABLE IF NOT EXISTS query_vectors '
                   '(cache_key TEXT PRIMARY KEY, revision TEXT NOT NULL, model TEXT NOT NULL, '
                   'dimensions INTEGER NOT NULL, vector TEXT NOT NULL, used_at INTEGER NOT NULL DEFAULT 0)')
        row=db.execute('SELECT vector FROM query_vectors WHERE cache_key=? AND revision=? '
                       'AND model=? AND dimensions=?',(key,index['revision'],MODEL,index['dimensions'])).fetchone()
        if row:
            db.execute('UPDATE query_vectors SET used_at=unixepoch() WHERE cache_key=?',(key,))
            return json.loads(row[0])
        response=embed([query],'RETRIEVAL_QUERY')
        if len(response)!=1:return None
        vector=response[0]
        db.execute('INSERT OR REPLACE INTO query_vectors '
                   '(cache_key,revision,model,dimensions,vector,used_at) VALUES (?,?,?,?,?,unixepoch())',
                   (key,index['revision'],MODEL,index['dimensions'],json.dumps(vector,separators=(',',':'))))
        db.execute('DELETE FROM query_vectors WHERE cache_key IN '
                   '(SELECT cache_key FROM query_vectors ORDER BY used_at DESC LIMIT -1 OFFSET 1000)')
        return vector


def search_index(query,data,index,*,embed,cache_path=None):
    expected=[c['id'] for c in data['chunks'] if c['curriculum_status']=='primary']
    if (index['revision']!=fingerprint(data) or index['model']!=MODEL
        or [r['id'] for r in index['rows']]!=expected):raise ValueError('Stale or incomplete vector index')
    vector=_cached_query_vector(query,index,embed,cache_path)
    if vector is None:raise ValueError('Invalid query embedding')
    q=unit(vector);scores={}
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
