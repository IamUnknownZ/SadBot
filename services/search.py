"""Heading-first, complete parent retrieval plus full-vocabulary BM25/vector search."""
import math
import re
import unicodedata
from collections import Counter

# Human-reviewed query synonyms, not a translated corpus or answer source.
ALIASES={
 'บับเบิลซอร์ท':['bubble sort'], 'บับเบิลซอร์ต':['bubble sort'],
 'บับเบิลซอส':['bubble sort'], 'เรียงแบบฟอง':['bubble sort'], 'ฟองสบู่':['bubble sort'],
 'ซีเล็กชันซอร์ท':['selection sort'], 'ซีเล็กชั่นซอร์ท':['selection sort'],
 'ซีเลคชันซอร์ท':['selection sort'], 'เรียงแบบเลือก':['selection sort'], 'เลือกค่าต่ำสุด':['selection sort'],
 'อินเซอร์ชันซอร์ท':['insertion sort'], 'อินเซิร์ชันซอร์ท':['insertion sort'],
 'เรียงแบบแทรก':['insertion sort'], 'จัดไพ่ในมือ':['insertion sort'],
 'เมิร์จซอร์ท':['merge sort'], 'เมอร์จซอร์ท':['merge sort'], 'เรียงแบบผสาน':['merge sort'],
 'เคาน์ติ้งซอร์ท':['counting sort'], 'เคาน์ทิงซอร์ท':['counting sort'],
 'เรียงแบบนับ':['counting sort'], 'นับความถี่':['counting sort'],
 'ประสิทธิภาพต่ำ':['inefficient','quadratic','running time','comparisons'],
 'ประสิทธิภาพ':['efficiency','performance'], 'สมรรถนะ':['efficiency','performance'], 'performance':['inefficiency'],
 'inefficient':['quadratic','running time','comparisons'], 'inefficiency':['quadratic','running time','comparisons'],
 'ช้า':['quadratic','running time','comparisons'], 'ประสิทธิภาพไม่ดี':['inefficient','quadratic','running time'],
 'ความเร็ว':['running time','efficiency'], 'ใช้เวลา':['running time'], 'เวลา':['time'],
 'พื้นที่':['space'], 'หน่วยความจำ':['memory','space'], 'ต้นทุน':['cost'],
 'เสถียร':['stability','stable'], 'คีย์':['key'], 'ข้อมูล':['data'],
 'หลักการเรียงลำดับ':['principles of sorting'], 'หลักการเรียง':['principles of sorting'],
 'บทนำ':['introduction'], 'สารบัญ':['contents'], 'ลิขสิทธิ์':['copyright'],
 'ขอบเขตล่าง':['lower bounds'], 'ขอบเขตบน':['upper bound'], 'สัญกรณ์':['notation'],
 'อัตราการเติบโต':['order of growth'], 'ความซับซ้อน':['complexity','running time'],
 'แบบเลวร้าย':['worst case'], 'กรณีแย่ที่สุด':['worst case'], 'เฉลี่ย':['average'],
 'กรณีดีที่สุด':['best case'], 'กรณีเฉลี่ย':['average case'],
 'เรียงจากน้อยไปมาก':['ascending order'], 'น้อยไปมาก':['ascending order'],
 'เรียงจากมากไปน้อย':['descending order'], 'มากไปน้อย':['descending order'],
 'จากซ้ายไปขวา':['left to right'], 'จากขวาไปซ้าย':['right to left'],
 'จำนวนการเปรียบเทียบ':['comparisons'], 'เปรียบเทียบ':['comparison','compare'],
 'ข้อดีและข้อเสีย':['advantages','disadvantages','strengths','limitations'],
 'ข้อดีข้อเสีย':['advantages','disadvantages','strengths','limitations'],
 'ข้อดี':['advantages','benefits','strengths'],
 'ข้อเสีย':['disadvantages','drawbacks','limitations','inefficient'],
 'ข้อจำกัด':['limitations','constraints'], 'จุดเด่น':['advantages','strengths'],
 'จุดด้อย':['disadvantages','limitations'], 'ประโยชน์':['benefits','useful'],
 'เหมาะกับ':['suitable','practical','appropriate'], 'เหมาะเมื่อ':['suitable','practical'],
 'ควรใช้เมื่อ':['choose','practice','appropriate'], 'ใช้ตอนไหน':['choose','practice'],
 'ใช้เมื่อไร':['choose','practice'], 'เลือกใช้':['choose','practice'],
 'ทำไมถึง':['why','reason'], 'เหตุผล':['reasons','why'],
 'การผกผัน':['inversions'], 'ถูกต้อง':['correctness'], 'เงื่อนไข':['conditions'],
 'คู่ผกผัน':['inversions'], 'การเรียกซ้ำ':['recursion','recursive'],
 'รีเคอร์ซีฟ':['recursive','recursion'], 'สแตกโอเวอร์โฟลว์':['stack overflow'],
 'สแต็กโอเวอร์โฟลว์':['stack overflow'], 'ต้นไม้ตัดสินใจ':['decision tree'],
 'ต้นไม้การตัดสินใจ':['decision tree'], 'แบ่งแล้วพิชิต':['divide and conquer'],
 'แบ่งแยกและเอาชนะ':['divide and conquer'], 'ผลรวมสะสม':['cumulative counts','prefix sum'],
 'เปรียบเทียบแบบต้นไม้':['decision tree','comparison sort'],
 'ข้อมูลซ้ำ':['equal keys','duplicates'], 'คีย์ซ้ำ':['equal keys'],
 'อยู่กับที่':['in place'], 'อินเพลส':['in place'], 'สลับ':['exchange','swap'],
 'ติดกัน':['adjacent'], 'หนึ่งรอบ':['one pass'], 'แต่ละรอบ':['pass'],
 'รหัสเทียม':['pseudocode'], 'โค้ด':['code','implementation'], 'ขั้นตอน':['trace'],
 'ทีละขั้น':['trace'], 'เลือก':['selection'], 'แทรก':['insertion'], 'ผสาน':['merge'],
 'ฟอง':['bubble'], 'นับจำนวน':['counting'], 'อัลกอริทึม':['algorithms'],
 'นิยาม':['definition'], 'ตาราง':['table'], 'สูตร':['formula'], 'เทคโนโลยี':['technology'],
 'คอมพิวเตอร์':['computer'], 'ข้อมูลประกอบ':['satellite'], 'การเคลื่อนย้าย':['movement']}
STOP=set('the a an of in to is and or for as on with by from at this that how why what explain please does work works sort'.split())
THAI_WRAPPERS=['ทั้งบท','อ่าน','ช่วย','ขอ','อธิบาย','เกี่ยวกับ','เรื่อง','หัวข้อ','ทั้งหมด','คืออะไร','อย่างไร','หน่อย','ครับ','ค่ะ','มีอะไรบ้าง']


def normalize(text):
    return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',text).casefold()).strip()


def exact_phrase_lookup(query,data):
    """Return every complete source paragraph containing a copied phrase.

    This route is intentionally narrow: natural questions, Thai queries, short
    concept names, and exact headings continue through their existing routes.
    """
    phrase=normalize(query).strip(' \t\r\n"\'“”‘’`.,;:')
    if not phrase or re.search(r'[\u0e00-\u0e7f?？]',phrase):return []
    if len([token for token in terms(phrase) if token not in STOP])<3:return []
    if re.match(r'^(?:what|why|how|who|where|when|which|explain|describe|define|compare|show|tell|can|does|do|is|are|should|could)\b',phrase):return []
    from .retrieval import plan_query
    if plan_query(phrase)['intent']!='fact':return []
    if matched_headings(phrase,data):return []
    pattern=re.compile(r'(?<![a-z0-9])'+re.escape(phrase)+r'(?![a-z0-9])',re.I)
    groups={}
    for chunk in data.get('chunks',[]):
        if chunk.get('kind') not in ('paragraph','list'):continue
        key=(chunk.get('document_id'),chunk.get('paragraph_id') or chunk['id'])
        groups.setdefault(key,[]).append(chunk)
    matches=[]
    for rows in groups.values():
        rows.sort(key=lambda row:row.get('order',0))
        # Supplements carry a dataset-editor provenance footer that is not
        # instructional prose and must not make generic footer phrases match.
        source=' '.join(re.sub(r'(?im)^\s*New explanatory material;\s*original source:.*$','',
                               row.get('text','')) for row in rows)
        if not pattern.search(normalize(source)):continue
        matches.extend(dict(row,score=1.,retrieval_method='exact_phrase',matched_terms=terms(phrase)) for row in rows)
    return sorted(matches,key=lambda row:row.get('order',0))


def expanded(query):
    out=normalize(query)
    for th,words in sorted(ALIASES.items(),key=lambda x:-len(x[0])):
        if th in out:out=out.replace(th,' '+' '.join(words)+' ')
    return normalize(out)


def terms(text):return re.findall(r'[a-z]+(?:-[a-z]+)*|\d+|[\u0e00-\u0e7f]+',normalize(text))


def heading_query(query):
    q=normalize(query)
    for phrase in THAI_WRAPPERS:q=q.replace(phrase,' ')
    q=normalize(q)
    # These standalone terms refer to the source's "Efficiency" section.
    # Do not rewrite larger questions such as "performance of merge sort".
    if q in ('ประสิทธิภาพ','สมรรถนะ','performance'):
        return 'efficiency'
    q=expanded(q)
    q=re.sub(r'^(?:explain|what is|tell me about|show|describe)\s+','',q)
    return heading_name(normalize(q).strip(' ?!.'))


def heading_name(title):
    return normalize(re.sub(r'^(?:S?\d+(?:\.\d+)*[ .]+)','',title,flags=re.I)).strip(' ?!.')


def numbered_heading_parts(text):
    """Keep an explicit book heading number available for exact lookup."""
    match=re.match(r'^\s*(S?)(\d+(?:\.\d+)*)(?:[ .]+\s*)(.+?)\s*$',normalize(text),re.I)
    if not match:return None
    return (bool(match.group(1)),match.group(2),heading_name(match.group(3)))


def matched_headings(query,data):
    requested=numbered_heading_parts(query)
    if requested:
        is_supplement,number,title=requested
        numbered=[]
        for node in data.get('nodes',[]):
            if node['kind'] not in ('chapter','section','subsection'):continue
            candidate=numbered_heading_parts(node['title'])
            if candidate and candidate[1]==number:
                numbered.append((node,candidate))
        if is_supplement:
            numbered=[item for item in numbered if item[1][0]]
        else:
            regular=[item for item in numbered if not item[1][0]]
            if regular:numbered=regular
        # A real number with an unrelated title must not open a whole chapter.
        exact=[node for node,candidate in numbered if candidate[2]==title]
        if exact:return exact
        return [node for node,candidate in numbered if candidate[2].startswith(title)]
    queries={heading_query(query),heading_name(query)}
    return [n for n in data.get('nodes',[]) if n['kind'] in ('chapter','section','subsection') and heading_name(n['title']) in queries]


def has_numbered_heading_prefix(query):
    return numbered_heading_parts(query) is not None


def definition_cue(query):
    text=normalize(query)
    compact=re.sub(r'\s+','',text)
    return (any(p in compact for p in ['คืออะไร','หมายถึงอะไร','ความหมาย','นิยาม'])
            or bool(re.search(r'คือ\s*(?:ครับ|ค่ะ|คะ)?[ ?!.]*$',text))
            or any(compact.rstrip(' ?!.').endswith(re.sub(r'\s+','',normalize(p))) for p in ['ทำงานอย่างไร','ทำงานยังไง'])
            or bool(re.search(r'\b(?:what is|define|definition of|meaning of)\b',text)))


def _sorting_keyword_definition(query,data):
    from .retrieval import is_sorting_keyword
    if not is_sorting_keyword(query):return []
    chunks=data.get('chunks',[])
    start=next((i for i,c in enumerate(chunks)
                if c.get('curriculum_status')=='primary' and c.get('kind')=='paragraph'
                and 'formally define the sorting problem' in normalize(c.get('text',''))),None)
    if start is None:return []
    first=chunks[start]
    # Keep the definition, its Input/Output statement, and the source example
    # together as one compact answer instead of returning every use of "sort".
    selected=[]
    for c in chunks[start:start+3]:
        if (c.get('curriculum_status')!='primary' or c.get('kind')!='paragraph'
            or c.get('page')!=first.get('page') or c.get('parent_id')!=first.get('parent_id')):
            break
        selected.append(dict(c,score=1.,retrieval_method='exact_keyword',matched_terms=['sort']))
    return selected


def definition_rows(query,data):
    """Select the source definition and reviewed introductory context, not a chapter."""
    compact=re.sub(r'\s+','',normalize(query))
    from .retrieval import plan_query,TOPICS
    plan=plan_query(query)
    if len(plan['topics'])!=1 or plan['intent'] in ('steps','comparison','code','complexity','stability'):return []
    topic=plan['topics'][0]
    if topic=='principles':return _sorting_keyword_definition(query,data)
    bare=compact in {re.sub(r'\s+','',normalize(alias)) for alias in TOPICS[topic]}
    if not (bare or definition_cue(query)):return []
    pattern=re.compile(r'\b'+re.escape(topic)+r'\s*sort\s+(?:algorithm\s+(?:closely\s+)?)?(?:is|works|repeatedly|divides|assumes|uses|follows|exploits)\b',re.I)
    candidates=[];context=[]
    # Source heading routes, not generated answers. Include mechanics and pass
    # direction needed to understand the definition; exclude exercises and traces.
    context_titles={'bubble':{'the basic operation','the clrs direction'}}.get(topic,set())
    for c in data['chunks']:
        if c['kind']!='paragraph' or c.get('topic')!=topic:continue
        page=data['pages'][c['page']-1]
        lines=[l for l in page['lines'] if l['id'] in c['line_ids']]
        if c.get('contains_heading') and lines and normalize(lines[0]['text'])==normalize(c['title']):lines=lines[1:]
        if not lines:continue
        start,end=lines[0]['char_start'],lines[-1]['char_end']
        text=page['text'][start:end]
        defining=bool(pattern.search(normalize(text)))
        introductory=normalize(c['title']) in context_titles
        if not defining and not introductory:continue
        boxes=[l['bbox'] for l in lines]
        row=dict(c,text=text,char_start=start,char_end=end,line_ids=[l['id'] for l in lines],
                 bbox=[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)],
                 contains_heading=False,score=1.,retrieval_method='definition')
        if defining:candidates.append(row)
        if introductory:context.append(row)
    from .translation import UNSAFE
    candidates.sort(key=lambda c:(bool(UNSAFE.search(c['text'])),c.get('source_kind')!='original',c['order']))
    if not candidates:return []
    first=candidates[0]
    selected={first['id']:first}
    # A prose introduction ending in ':' may introduce source-listed steps.
    # Preserve those steps, without opening the whole chapter.
    if first['text'].rstrip().endswith(':'):
        for c in data['chunks']:
            if (first['order']<c['order']<=first['order']+3 and c['parent_id']==first['parent_id']
                and c['page']==first['page'] and c['kind'] in ('paragraph','list')):
                selected[c['id']]=dict(c,score=1.,retrieval_method='definition')
    for row in context:
        if row['chapter_id']==first['chapter_id']:selected[row['id']]=row
    return sorted(selected.values(),key=lambda c:c['order'])


def lexical_index(data):
    docs={c['id']:Counter(t for t in terms(' '.join(c['heading_path'])+' '+c['text']) if t not in STOP) for c in data['chunks']}
    df=Counter(t for doc in docs.values() for t in doc)
    return dict(schema_version=1,document_sha256=data['document']['sha256'],vocabulary=sorted(df),
                document_frequency=dict(df),documents={k:dict(v) for k,v in docs.items()})


def needs_dense_search(query,data):
    """Reserve query embeddings for searches that local BM25 cannot cover."""
    if matched_headings(query,data) or definition_rows(query,data) or exact_phrase_lookup(query,data):
        return False
    query_terms={t for t in terms(expanded(query))
                 if t not in STOP and re.search(r'[a-z]',t)}
    if not query_terms:
        return True
    rows=hybrid_retrieve(query,data,limit=8,candidate_mode=True)
    if not rows:
        return True
    # Continuation chunks can share a paragraph and match list. Compare unique
    # terms so paragraph splitting cannot inflate lexical confidence.
    matches=[set(row.get('matched_terms',[])) for row in rows]
    best=max(matches,key=len,default=set())
    covered=set().union(*matches[:4]) if matches else set()
    coverage=len(covered & query_terms)/len(query_terms)
    best_coverage=len(best & query_terms)/len(query_terms)
    if len(query_terms)<=2:
        return not query_terms.issubset(covered)
    return not (best_coverage>=0.60 or (len(best)>=2 and coverage>=0.75))


def hybrid_retrieve(query,data,limit=12,dense_scores=None,section_id=None,candidate_mode=False):
    from .retrieval import plan_query
    query=plan_query(query)['normalized']
    definition=definition_rows(query,data) if not section_id and not candidate_mode else []
    if definition:return definition
    nodes=data.get('nodes',[]);hits=matched_headings(query,data) if not candidate_mode else []
    routes=[g['target_section_id'] for g in data.get('query_guidance',[]) if normalize(g['query'])==normalize(query)]
    if routes and not hits and not candidate_mode:hits=[n for n in nodes if n['id'] in routes]
    if section_id:
        hits=[n for n in nodes if n['id']==section_id]
        if not hits:raise ValueError('Unknown source section')
    # Numbered title lookups are precise references, not a license to fall
    # back to lexical words from a differently titled numbered section.
    if not section_id and not candidate_mode and has_numbered_heading_prefix(query) and not hits:
        return []
    if not candidate_mode and not hits and any(t in normalize(query) for t in ['ทีละขั้น','ขั้นตอน','step by step']):
        from .retrieval import plan_query
        topic=plan_query(query)['topics']
        fragments={'bubble':'complete trace','selection':'complete trace','insertion':'saved key','merge':'ranges, recursion','counting':'histogram, cumulative'}
        if len(topic)==1:
            hits=[n for n in nodes if n['kind']=='section' and fragments.get(topic[0],'NOT FOUND') in normalize(n['title']) and topic[0] in normalize(n['title'])]
    if hits:
        ids={ident for n in hits for ident in n['chunk_ids']}
        return [dict(c,score=1.,retrieval_method='exact_heading',matched_heading_ids=[n['id'] for n in hits]) for c in data['chunks'] if c['id'] in ids]
    # No vocabulary allowlist: every parsed English word participates.
    q=set(t for t in terms(expanded(query)) if t not in STOP and not re.fullmatch(r'[\u0e00-\u0e7f]+',t))
    if candidate_mode:
        from .retrieval import plan_query
        q.update(t for t in plan_query(query)['topics'] if t!='principles')
    if not any(re.search('[a-z]',t) for t in q):q=set()
    index=data.get('keyword_index') or lexical_index(data)
    docs=index['documents'];df=index['document_frequency'];N=len(docs);avg=sum(sum(d.values()) for d in docs.values())/max(1,N)
    ranked=[]
    for c in data['chunks']:
        if candidate_mode and c['kind']=='heading':continue
        counts=docs[c['id']];length=sum(counts.values());score=0.;matched=[]
        if candidate_mode:
            # Repeated path words must not outrank actual explanatory body text.
            counts=Counter(t for t in terms(c['text']) if t not in STOP)
            length=sum(counts.values())
        for t in q:
            f=counts.get(t,0)
            if f:
                matched.append(t);idf=math.log(1+(N-df.get(t,0)+.5)/(df.get(t,0)+.5))
                score+=idf*f*2.2/(f+1.2*(.25+.75*length/max(1,avg)))
        dense=(dense_scores or {}).get(c['id'],0)
        ranked.append((score,dense,c,matched))
    # Lexical evidence and an absolute dense floor prevent unrelated top-1 answers.
    lexical=sorted([r for r in ranked if r[0]>0],key=lambda r:-r[0])
    vector=sorted([r for r in ranked if r[1]>=.66 and r[0]>0],key=lambda r:-r[1])
    if not lexical and not vector:return []
    fused={}
    for rows in [lexical,vector]:
        for rank,row in enumerate(rows):
            ident=row[2]['id'];fused[ident]=fused.get(ident,0)+1/(60+rank+1)
    chosen=sorted([r for r in ranked if r[2]['id'] in fused],key=lambda r:-fused[r[2]['id']])[:limit]
    # Pull every child of the matched paragraph, including continuation on the next page.
    paragraphs={r[2]['paragraph_id'] for r in chosen}
    scores={r[2]['paragraph_id']:fused[r[2]['id']] for r in chosen}
    found=[dict(c,score=scores[c['paragraph_id']],retrieval_method='hybrid',matched_terms=next((r[3] for r in chosen if r[2]['paragraph_id']==c['paragraph_id']),[]))
           for c in data['chunks'] if c['paragraph_id'] in paragraphs]
    return sorted(found,key=lambda c:(-c['score'],c['order']))
