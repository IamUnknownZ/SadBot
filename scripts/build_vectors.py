"""Build dense vectors in bounded, resumable batches from the current scan only."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import json
from dotenv import dotenv_values
import os
from services.ingest import load_dataset
from services.vectors import fingerprint,provider,build_index,MODEL,DIMENSIONS,unit,embedding_text


def main(language="en"):
    if language!="en":raise ValueError("English embeddings only")
    folder=ROOT/"vector_store"
    folder.mkdir(parents=True,exist_ok=True)
    key=os.getenv('GEMINI_API_KEY') or dotenv_values(ROOT/'.env').get('GEMINI_API_KEY')
    if not key:raise ValueError('No embedding key configured; offline search is available')
    data=load_dataset(ROOT,language=language);chunks=[c for c in data['chunks'] if c['curriculum_status']=='primary']
    revision=fingerprint(data);checkpoint=folder/'progress.json';rows=[]
    if checkpoint.exists():
        saved=json.loads(checkpoint.read_text())
        if saved['revision']==revision and saved['model']==MODEL:
            rows=saved['rows']
            if len(rows)>len(chunks):raise ValueError('Invalid checkpoint length')
            for c,row in zip(chunks,rows):
                if c['id']!=row['id'] or len(row['vector'])!=DIMENSIONS:raise ValueError('Invalid checkpoint')
                unit(row['vector'])
    embed=provider(key)
    status_file=folder/'status.json'
    def write_status(state,error=None):
        status_file.write_text(json.dumps(dict(state=state,model=MODEL,dimensions=DIMENSIONS,revision=revision,source_language='en',expected=len(chunks),completed=len(rows),error=error),indent=2)+'\n')
    write_status('building')
    for start in range(len(rows),len(chunks),24):
        batch=chunks[start:start+24]
        try:values=embed([embedding_text(c) for c in batch],'RETRIEVAL_DOCUMENT')
        except ValueError as exc:
            write_status('incomplete',str(exc));raise
        rows.extend(dict(id=c['id'],section_id=c['section_id'],source_page=c['page'],heading_path=c['heading_path'],vector=unit(v)) for c,v in zip(batch,values))
        checkpoint.write_text(json.dumps(dict(revision=revision,model=MODEL,rows=rows)))
        print(f'Embedded {len(rows)}/{len(chunks)} chunks',flush=True)
    dest=folder/'text_index.json'
    pending=dest.with_suffix('.pending')
    pending.write_text(json.dumps(dict(revision=revision,model=MODEL,dimensions=DIMENSIONS,document_task="RETRIEVAL_DOCUMENT",query_task="RETRIEVAL_QUERY",normalized=True,source_language="en",rows=rows)))
    pending.replace(dest);checkpoint.unlink(missing_ok=True)
    write_status('complete')
    print('Published complete current-source vector index')

if __name__=='__main__':
    try:main("th" if "--language=th" in sys.argv else "en")
    except ValueError as exc:print(str(exc));sys.exit(1)
