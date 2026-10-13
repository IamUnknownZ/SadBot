"""Layout-aware hierarchy built from the PDF's bookmarks and original line spans."""
import hashlib
import re
from collections import Counter
import pymupdf


def union(lines):
    rect=pymupdf.Rect(lines[0]['bbox'])
    for line in lines[1:]:rect |= pymupdf.Rect(line['bbox'])
    return list(rect)


def heading(line,body_size):
    text=line['text'].strip();spans=line['spans']
    if not text or len(text)>125 or text.endswith(('.', ';', ',')):return False
    if re.match(r'^(?:\d+\s+(?:for|while|if|else|return)|//|def |for |while |return |Q:|A:)',text):return False
    if any('Courier' in s['font'] for s in spans):return False
    size=max(s['size'] for s in spans)
    bold=sum(len(s['text'].strip()) for s in spans if 'Bold' in s['font'])/max(1,len(text.replace(' ','')))
    # Bold emphasis inside prose is not a heading. Numbering, size, and geometry also matter.
    return bool(size>=body_size+1 or (bold>=.9 and len(text.split())<=16 and len(text)>=4))


def classify(lines):
    text='\n'.join(l['text'] for l in lines)
    fonts=[s['font'] for l in lines for s in l['spans']]
    if any('Courier' in f for f in fonts) or re.search(r'(?m)^\s*(?:def |for .*(?: to | in )|while |return |\d+\s+(?:for|while|if))',text):return 'code'
    if re.match(r'^Figure\s+\d',text):return 'caption'
    if re.match(r'^\s*(?:[•▪]|[a-z]\.\s)',text):return 'list'
    if sum(bool(re.search(r'\s{3,}',l['text'])) for l in lines)>2:return 'table'
    if sum('MT2' in f or 'Symbol' in f for f in fonts)>len(fonts)*.6:return 'formula'
    return 'paragraph'


def build_structure(data,toc=(),*,max_chars=1800):
    doc=data['document'];nodes=[];chunks=[];lookup={}
    def node(kind,title,parent,level,page,bbox=None):
        ident=f'{doc["id"]}-{kind}-{len(nodes):04d}'
        path=(lookup[parent]['heading_path'] if parent else [])+[title]
        n=dict(id=ident,kind=kind,title=title,parent_id=parent,heading_level=level,document_id=doc['id'],
               page_start=page,page_end=page,source_page=page,bbox=bbox,heading_path=path,child_ids=[],chunk_ids=[])
        nodes.append(n);lookup[ident]=n
        if parent:lookup[parent]['child_ids'].append(ident)
        return ident
    root=node('document',doc['title'],None,0,1)
    chapter=section=subsection=None;previous=None;exercise_parent=None
    chapter_marks={page:title for level,title,page in toc if level==1}
    section_marks={page:title for level,title,page in toc if level==2}
    topic_names=['principles','bubble','selection','insertion','merge','counting']
    for page in data['pages']:
        number=page['page'];page_lines=page['lines']
        if number in chapter_marks:
            chapter=node('chapter',chapter_marks[number],root,1,number);section=subsection=None;exercise_parent=None
        if chapter is None:
            chapter=node('chapter','Front matter' if toc else 'Document content',root,1,number)
        if number in section_marks:
            section=node('section',section_marks[number],chapter,2,number);subsection=None;exercise_parent=None
        if section is None or (toc and number<=4):
            section=node('section',('Cover','Title page','Copyright','Contents')[number-1] if toc and number<=4 else 'Introduction',chapter,2,number)
        body=[l for l in page_lines if l['role']!='running_header']
        # Estimate prose size from regular text, not small diagram labels,
        # mathematical scripts, code, or emphasized spans.
        prose=[s for l in body if l['role']!='figure_label' for s in l['spans']
               if not any(f in s['font'] for f in ('MT2','Symbol','Courier','Bold','Italic'))]
        sizes=Counter(round(s['size'],1) for s in prose for _ in s['text'].strip())
        if not sizes:
            sizes=Counter(round(s['size'],1) for l in body if l['role']!='figure_label' for s in l['spans'] for _ in s['text'].strip())
        body_size=sizes.most_common(1)[0][0] if sizes else 11
        groups=[];group=[];group_kind=None
        skip=False
        for idx,line in enumerate(body):
            if skip:skip=False;continue
            if (re.fullmatch(r'\d+(?:\.\d+)*',line['text'].strip()) and idx+1<len(body)
                and abs(body[idx+1]['bbox'][1]-line['bbox'][1])<4 and heading(body[idx+1],body_size)):
                if group:groups.append((group,False));group=[]
                groups.append(([line,body[idx+1]],True));skip=True;continue
            is_heading=line['role']!='figure_label' and heading(line,body_size)
            if number<=4 and toc:is_heading=False
            # Source chapter title, supplement title, and numbered sections are level 2.
            numbered=bool(re.match(r'^(?:S\d+\.\d+|\d+\.\d+(?:\.\d+)?\s)',line['text']))
            if is_heading:
                if group:groups.append((group,False));group=[]
                groups.append(([line],True));continue
            if group:
                last=group[-1];gap=line['bbox'][1]-last['bbox'][3]
                indent=line['bbox'][0]-last['bbox'][0]
                new_block=line['block_id']!=last['block_id']
                if line['role']!=last['role'] or gap>4 or (new_block and gap>1) or (indent>8 and last['text'].rstrip().endswith(('.',':',';'))):
                    groups.append((group,False));group=[]
            group.append(line)
        if group:groups.append((group,False))
        for lines,is_heading in groups:
            if is_heading:
                text=' '.join(l['text'].strip() for l in lines)
                numbered=bool(re.match(r'^(?:S\d+\.\d+|\d+\.\d+(?:\.\d+)?\s)',text))
                # Bookmarked headings already have a parent section at the page start.
                if section_marks.get(number)==text:
                    lookup[section]['bbox']=lines[0]['bbox'];subsection=None;exercise_parent=None
                elif numbered:
                    section=node('section',text,chapter,2,number,lines[0]['bbox']);subsection=None;exercise_parent=None
                else:
                    exercise_number=bool(re.fullmatch(r'\d+(?:\.\d+)+-\d+',text))
                    owner=exercise_parent if exercise_number and exercise_parent else section
                    subsection=node('subsection',text,owner,lookup[owner]['heading_level']+1,number,lines[0]['bbox'])
                    if text.casefold()=='exercises':exercise_parent=subsection
                    elif not exercise_number:exercise_parent=None
            parent=subsection or section
            kind='heading' if is_heading else ('figure_label' if lines[0]['role']=='figure_label' else classify(lines))
            first,last=lines[0],lines[-1]
            continuation=(not is_heading and previous and previous['parent_id']==parent and previous['page_end']==number-1
                          and previous.get('content_type')=='paragraph' and not previous.get('last_text','').rstrip().endswith(('.',':',';','?','!')))
            paragraph=previous['id'] if continuation else node('paragraph',f'Paragraph {len(chunks)+1}',parent,lookup[parent]['heading_level']+1,number,union(lines))
            lookup[paragraph]['page_end']=number;lookup[paragraph]['last_text']=last['text']
            # Long paragraphs split only at actual source line boundaries, with no lost lines.
            batches=[];batch=[];length=0
            for line in lines:
                if batch and length+len(line['text'])>max_chars:batches.append(batch);batch=[];length=0
                batch.append(line);length+=len(line['text'])+1
            if batch:batches.append(batch)
            for batch in batches:
                a,b=batch[0],batch[-1];path=lookup[parent]['heading_path']
                c=dict(id=f'p{number}-c{len(chunks):04d}',document_id=doc['id'],source_sha256=doc['sha256'],
                    page=number,source_page=number,page_start=number,page_end=number,bbox=union(batch),
                    char_start=a['char_start'],char_end=b['char_end'],line_ids=[l['id'] for l in batch],
                    text=page['text'][a['char_start']:b['char_end']],kind=kind,
                    title=lookup[parent]['title'],heading_path=path,heading_level=lookup[parent]['heading_level'],
                    chapter_id=chapter,section_id=section,subsection_id=subsection,parent_id=parent,paragraph_id=paragraph,
                    topic=page['topic'],curriculum_status='primary',order=len(chunks),intents=[],
                    source_kind=page['source_kind'])
                # Exact math/code glyph spans remain available to protect during translation.
                c['protected_spans']=[s['text'] for l in batch for s in l['spans']
                    if ('MT2' in s['font'] or 'Symbol' in s['font'] or 'Courier' in s['font']) and s['text'].strip()]
                chunks.append(c)
                current=paragraph
                while current:
                    n=lookup[current];n['chunk_ids'].append(c['id']);n['page_end']=number;current=n['parent_id']
            previous=lookup[paragraph];previous['kind']=kind if kind!='heading' else 'heading'
            # Paragraph nodes retain their hierarchy kind separately from content type.
            previous['content_type']=previous['kind'];previous['kind']='paragraph'
        page['section_ids']=list(dict.fromkeys(c['section_id'] for c in chunks if c['page']==number))
    for n in nodes:n.pop('last_text',None)
    data.update(schema_version=3,nodes=nodes,chunks=chunks,chunking=dict(strategy='layout-paragraph',max_chars=max_chars,overlap=0,
        rationale='Disjoint source lines; full parent expansion supplies context without duplicated evidence.'))
    return merge_heading_children(exclude_editor_qa(data),max_chars)


def exclude_editor_qa(data):
    """Keep authored Q&A out of evidence and vectors; questions only route to parents."""
    nodes={n['id']:n for n in data['nodes']}
    qa={n['id'] for n in data['nodes'] if n['kind'] in ('section','subsection') and n['title'].strip().casefold()=='semantic questions and answers'}
    removed=[];kept=[];guidance=[]
    for c in data['chunks']:
        if c['parent_id'] in qa:
            # Actual diagrams/captions following Q&A still belong to the source section.
            if c['kind']=='table' or c['text'].startswith(('Figure ','New explanatory material;')):
                parent=nodes[c['section_id']]
                c.update(parent_id=parent['id'],subsection_id=None,title=parent['title'],heading_path=parent['heading_path'],heading_level=parent['heading_level'])
                nodes[c['paragraph_id']]['parent_id']=parent['id']
                kept.append(c)
            else:removed.append(c)
        else:kept.append(c)
    for node_id in qa:
        group=[c for c in removed if c['parent_id']==node_id]
        text=' '.join(c['text'].replace('\n',' ') for c in group if c['kind']!='heading')
        for question,answer in re.findall(r'Q:\s*(.*?)\s*A:\s*(.*?)(?=\s*Q:|$)',text,re.S):
            guidance.append(dict(query=question.strip(),target_section_id=nodes[node_id]['parent_id'],
                source_page=nodes[node_id]['source_page'],provenance='editor-added QA; routing only, never answer evidence'))
    excluded_lines={l for c in removed for l in c['line_ids']}
    for page in data['pages']:
        for line in page['lines']:
            if line['id'] in excluded_lines:line['role']='editor_qa_excluded'
    retained_paragraphs={c['paragraph_id'] for c in kept}
    data['nodes']=[n for n in data['nodes'] if n['id'] not in qa and (n['kind']!='paragraph' or n['id'] in retained_paragraphs)]
    nodes={n['id']:n for n in data['nodes']}
    for n in nodes.values():n['chunk_ids']=[];n['child_ids']=[]
    for n in nodes.values():
        if n['parent_id'] in nodes:nodes[n['parent_id']]['child_ids'].append(n['id'])
    for c in kept:
        ident=c['paragraph_id']
        while ident:
            nodes[ident]['chunk_ids'].append(c['id']);ident=nodes[ident]['parent_id']
    data['chunks']=kept;data['query_guidance']=guidance
    data['exclusions']=dict(editor_qa_headings=len(qa),editor_qa_chunks=len(removed),editor_qa_line_ids=sorted(excluded_lines))
    return data


def merge_heading_children(data,max_chars):
    """Attach small headings to their own first paragraph, never another parent."""
    output=[];discarded=set();chunks=data['chunks'];i=0
    while i<len(chunks):
        current=chunks[i]
        if i+1<len(chunks):
            nxt=chunks[i+1]
            if (current['kind']=='heading' and nxt['kind'] in ('paragraph','list') and current['parent_id']==nxt['parent_id']
                and current['page']==nxt['page'] and nxt['char_end']-current['char_start']<=max_chars):
                merged=dict(nxt,char_start=current['char_start'],bbox=union([current,nxt]),
                    line_ids=current['line_ids']+nxt['line_ids'],order=current['order'],contains_heading=True)
                merged['text']=data['pages'][current['page']-1]['text'][merged['char_start']:merged['char_end']]
                discarded.add(current['paragraph_id']);output.append(merged);i+=2;continue
        output.append(current);i+=1
    data['chunks']=output;data['nodes']=[n for n in data['nodes'] if n['id'] not in discarded]
    nodes={n['id']:n for n in data['nodes']}
    for n in nodes.values():n['chunk_ids']=[];n['child_ids']=[c for c in n['child_ids'] if c in nodes]
    for c in output:
        ident=c['paragraph_id']
        while ident:
            nodes[ident]['chunk_ids'].append(c['id']);ident=nodes[ident]['parent_id']
    return data
