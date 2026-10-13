"""Rebuild text and coordinates from the current PDF; never import old indexes."""
import hashlib
import json
from pathlib import Path
import pymupdf
from .retrieval import TOPICS, INTENTS, compact

PUA=dict(zip(range(0xF700,0xF71E),[0xE10,0xE34,0xE35,0xE36,0xE37,0xE48,0xE49,0xE4A,0xE4B,0xE4C,0xE48,0xE49,0xE4A,0xE4B,0xE4C,0xE0D,0xE31,0xE4D,0xE47,0xE48,0xE49,0xE4A,0xE4B,0xE4C,0xE38,0xE39,0xE3A,0xE0E,0xE0F,0xE2C]))


def span_text(span):
    text=span['text']
    if span['font'] in ('THSarabunPSK','THSarabunPSK-Bold'):
        return text.translate(PUA)
    return text


def safe_path(root,name):
    path=(Path(root)/name).resolve()
    if not path.is_relative_to(Path(root).resolve()) or not path.is_file():
        raise ValueError('Dataset asset is missing or outside the project')
    return path


def rect_union(lines):
    r=pymupdf.Rect(lines[0]['bbox'])
    for line in lines[1:]: r |= pymupdf.Rect(line['bbox'])
    return list(r)


def extract_document(source,root,figure_specs=(),*,language="en",max_chars=1800):
    from .structure import build_structure
    if language!='en':raise ValueError('English source only; Thai PDF is for human reference outside runtime')
    source,root=Path(source).resolve(),Path(root).resolve()
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    data=dict(schema_version=3,document=dict(id='book-en',file=str(source.relative_to(root)),
        title='Basic Sorting Algorithms — English source and labeled supplements' if source.stem=='Cormen_Basic_Sorting_100_Pages' else source.stem,
        sha256=digest,language='en'),pages=[],chunks=[],images=[])
    specs={}
    for spec in figure_specs:specs.setdefault(spec['page'],[]).append(spec)
    with pymupdf.open(source) as pdf:
        from .math_repair import VerifiedMathDecoder
        decoder=VerifiedMathDecoder(pdf,root/'metadata/math_glyph_map.json')
        if decoder.enabled:data['document']['text_repair_revision']=decoder.revision
        data['document']['page_count']=len(pdf);toc=pdf.get_toc();data['bookmarks']=toc
        for number,page in enumerate(pdf,1):
            lines=[];text=''
            blocks=decoder.blocks(page)
            for block_id,block in enumerate(blocks):
                if block['type']!=0:continue
                for line in block['lines']:
                    spans=[dict(text=s['text'],raw_text=s.get('raw_text',s['text']),font=s['font'],size=s['size'],bbox=list(s['bbox']),
                                repairs=s.get('repairs',[])) for s in line['spans']]
                    value=''.join(s['text'] for s in spans).rstrip()
                    if not value.strip():continue
                    start=len(text);text+=value+'\n'
                    rect=pymupdf.Rect(line['bbox']);role='body'
                    if toc and len(pdf)==100 and number>4 and (rect.y1<55 or rect.y0>page.rect.height-30):role='running_header'
                    if any(pymupdf.Rect(s['bbox']).intersects(rect) for s in specs.get(number,[]) if s.get('kind')!='text_screenshot'):
                        role='figure_label'
                    lines.append(dict(id=f'p{number}-l{len(lines)+1}',text=value,raw_text=''.join(s['raw_text'] for s in spans).rstrip(),bbox=list(rect),
                        char_start=start,char_end=len(text)-1,spans=spans,block_id=block_id,role=role,
                        bold=all('Bold' in s['font'] for s in spans if s['text'].strip())))
            topic=next((t for a,b,t in [(34,44,'bubble'),(45,53,'selection'),(54,71,'insertion'),(72,89,'merge'),(90,100,'counting')] if toc and a<=number<=b),'principles')
            if not toc:topic=next((t for t,aliases in TOPICS.items() if any(compact(a) in compact(text) for a in aliases)),topic)
            data['pages'].append(dict(page=number,text=text,lines=lines,topic=topic,status='primary',
                source_kind='supplement' if 'Supplement S' in text[:180] else 'original',
                text_layer=bool(lines),embedded_images=len(page.get_images()),vector_paths=len(page.get_drawings()),
                visual_review='100-page contact-sheet audit 2026-10-13',width=page.rect.width,height=page.rect.height))
        return attach_reviewed_routes(build_structure(data,toc,max_chars=max_chars),root)


def attach_reviewed_routes(data,root):
    """Restore reviewed question routes after PDF cleanup; never import answers."""
    path=Path(root)/'metadata/reviewed_query_routes.json'
    if not path.is_file():return data
    source=json.loads(path.read_text())
    if source.get('source_sha256')!=data['document']['sha256']:return data
    from .search import normalize
    existing={normalize(g['query']) for g in data.get('query_guidance',[])}
    for route in source.get('routes',[]):
        targets=[n for n in data['nodes'] if n['kind'] in ('section','subsection')
                 and normalize(n['title'])==normalize(route['target_title'])
                 and n['page_start']<=route['source_page']<=n['page_end']]
        if len(targets)!=1:raise ValueError('Reviewed query route has no unique source section')
        if normalize(route['query']) in existing:continue
        data['query_guidance'].append(dict(query=route['query'],target_section_id=targets[0]['id'],
            source_page=route['source_page'],provenance='Reviewed question route; original Q&A archived outside runtime; never answer evidence'))
        existing.add(normalize(route['query']))
    return data


def validate_dataset(data,root):
    doc=data['document'];path=safe_path(root,doc['file'])
    if hashlib.sha256(path.read_bytes()).hexdigest()!=doc['sha256']:
        raise ValueError('Source PDF has changed; rebuild the dataset')
    if len(data['pages'])!=doc['page_count']:
        raise ValueError('Incomplete page scan')
    ids=set()
    with pymupdf.open(path) as pdf:
        for c in data['chunks']:
            page=data['pages'][c['page']-1]
            if c['id'] in ids or c['source_sha256']!=doc['sha256'] or c['text']!=page['text'][c['char_start']:c['char_end']]:
                raise ValueError('Evidence differs from the source scan')
            ids.add(c['id'])
            if not pdf[c['page']-1].rect.contains(pymupdf.Rect(c['bbox'])):
                raise ValueError('Evidence coordinates exceed the page')
        for image in data['images']:
            safe_path(root,image['file'])
            if image['source_sha256']!=doc['sha256'] or not set(image['linked_chunk_ids'])<=ids:
                raise ValueError('Image links differ from the current source')
    return data


def load_dataset(root,language="en"):
    if language!='en':raise ValueError('English dataset only; Thai reference is excluded from runtime')
    root=Path(root)
    data=json.loads((root/'metadata/dataset.json').read_text())
    if data.get('schema_version')!=3 or data['document']['language']!='en':
        raise ValueError('English hierarchical dataset must be rebuilt')
    # Older saved datasets called figure text tables; recover its visual role from the source line metadata.
    lines_by_page={page['page']:{line['id']:line for line in page['lines']} for page in data['pages']}
    for chunk in data['chunks']:
        if chunk.get('kind')!='table':continue
        lines=[lines_by_page[chunk['page']].get(ident) for ident in chunk.get('line_ids',[])]
        if lines and all(line and line.get('role')=='figure_label' for line in lines):
            chunk['kind']='figure_label'
    return validate_dataset(data,root)
