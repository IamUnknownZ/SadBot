"""Rebuild the English-only hierarchical dataset and full-vocabulary keyword index."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import hashlib
import json
import pymupdf
from PIL import Image
from services.ingest import extract_document,validate_dataset
from services.search import lexical_index

SOURCE=ROOT/'book_data/Cormen_Basic_Sorting_100_Pages.pdf'


def scan(language='en',max_chars=1800,write_images=True):
    if language!='en':raise ValueError('English source only')
    meta=ROOT/'metadata';meta.mkdir(exist_ok=True)
    specs=json.loads((meta/'figure_specs.json').read_text())
    data=extract_document(SOURCE,ROOT,specs,language='en',max_chars=max_chars)
    with pymupdf.open(SOURCE) as pdf:
        for spec in specs:
            page=pdf[spec['page']-1];rect=pymupdf.Rect(spec['bbox'])
            if not page.rect.contains(rect):raise ValueError('Invalid figure crop')
            file=f'assets/images/en/p{spec["page"]:03d}-{spec["id"]}.webp'
            if write_images:
                (ROOT/file).parent.mkdir(parents=True,exist_ok=True)
                pix=page.get_pixmap(matrix=pymupdf.Matrix(2,2),clip=rect,alpha=False)
                Image.frombytes('RGB',(pix.width,pix.height),pix.samples).save(ROOT/file,'WEBP',lossless=True)
            elif not (ROOT/file).is_file():raise ValueError('Text-only rebuild requires existing reviewed images')
            chunks=[c for c in data['chunks'] if c['page']==spec['page']]
            # A figure belongs to its containing PDF section, not a guessed global topic.
            section=next((c['section_id'] for c in chunks if c['bbox'][1]<rect.y0),chunks[0]['section_id'])
            linked=[c for c in chunks if c['section_id']==section]
            chapter=linked[0]['chapter_id'];path=next(n['heading_path'] for n in data['nodes'] if n['id']==section)
            data['images'].append(dict(spec,file=file,image_file=file,image_id=spec['id'],
                topic=data['pages'][spec['page']-1]['topic'],source_page=spec['page'],
                document_id=data['document']['id'],source_document=data['document']['id'],source_sha256=data['document']['sha256'],
                source_kind=data['pages'][spec['page']-1]['source_kind'],
                chapter_id=chapter,section_id=section,linked_section_id=section,subsection_id=None,heading_path=path,
                linked_chunk_ids=[c['id'] for c in linked],caption=spec.get('source_caption',spec['title']),
                verified=spec.get('verified',False) and spec.get('reviewed_source_sha256')==data['document']['sha256']))
    data['keyword_index']=lexical_index(data)
    validate_dataset(data,ROOT)
    for name,value in [('dataset',data),('documents',[data['document']]),('chunks',data['chunks']),('images',data['images']),('page_audit',data['pages']),('hierarchy',data['nodes']),('keyword_index',data['keyword_index']),('query_guidance',data['query_guidance'])]:
        pending=meta/f'{name}.pending';pending.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');pending.replace(meta/f'{name}.json')
    (meta/'collection.json').write_text(json.dumps(dict(schema_version=3,source_language='en',documents=[data['document']['file']],dataset='metadata/dataset.json',vectors='vector_store/text_index.json'),indent=2)+'\n')
    print(f'Scanned {len(data["pages"])} pages; {len(data["chunks"])} chunks; {len(data["nodes"])} hierarchy nodes; {len(data["images"])} reviewed figures; {len(data["keyword_index"]["vocabulary"])} keyword terms')

if __name__=='__main__':
    if any(a=='--language=th' for a in sys.argv):raise SystemExit('Thai source disabled')
    scan(write_images='--text-only' not in sys.argv)
