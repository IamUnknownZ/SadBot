"""Query planning and a transparent offline vector-search baseline."""
import math
import json
from pathlib import Path
from functools import lru_cache
import re
import unicodedata
from collections import Counter
from difflib import get_close_matches

TOPICS = {
    'bubble': ['bubble sort', 'bubble', 'บับเบิล', 'บับเบิ้ล', 'บับเบิลซอส', 'บับเบิลซอร์ต', 'บับเบิลซอร์ท', 'ฟอง', 'bubbel sort','สลับตัวติดกัน','สลับเพื่อนข้าง'],
    'selection': ['selection sort', 'selection', 'ซีเลกชัน', 'เลือก'],
    'insertion': ['insertion sort', 'insertion', 'อินเซอร์ชัน', 'แทรก','จัดไพ่ในมือ'],
    'merge': ['merge sort', 'merge', 'เมิร์จ', 'ผสาน'],
    'counting': ['counting sort', 'counting', 'เคาน์ติง', 'นับจำนวน'],
    'principles': ['หลักการเรียง', 'การเรียงลำดับ', 'sorting', 'big o', 'big-o', 'สัญกรณ์','อัลกอริทึม','algorithm'],
}
INTENTS = {
    'comparison': [
        'เปรียบเทียบ','ต่างกัน','แตกต่าง','เทียบ','ต่างอย่างไร','ต่างยังไง',
        'ดีกว่า','เร็วกว่า','ช้ากว่า','เหมาะกว่า','ประหยัดกว่า','อันไหน','แบบไหน',
        'ตัวไหน','เลือกตัวไหน','ใช้ตัวไหนดี','ควรเลือก','ควรใช้','ข้อดีข้อเสีย',
        'ข้อดีและข้อเสีย','เหมือนกันไหม','เหมือนหรือต่าง',
        'compare','comparison','versus',' vs ','difference between','different from',
        'which is better','better than','pros and cons','advantages and disadvantages',
    ],
    'stability': ['เสถียร','stable','stability','คีย์เท่ากัน'],
    'complexity': ['ซับซ้อน','เวลา','พื้นที่','ต้นทุน','ประสิทธิภาพ','ประสิทธิภาพต่ำ','ความเร็ว','ช้า',
                   'complexity','big o','big-o','memory','efficiency','performance','inefficient','inefficiency','slow','quadratic'],
    'code': ['โค้ด','รหัสเทียม','โปรแกรม','code','pseudocode'],
    'steps': ['ทีละขั้น','ขั้นตอน','แต่ละรอบ','ไล่','ตัวอย่าง','step','trace','tee la khan'],
    'explanation': ['อธิบาย','ทำไม','อย่างไร','ยังไง','เพราะ','why','how','tam ngai'],
}

SORT_KEYWORD_RE = re.compile(
    r'^\s*(?:s[\s.-]*o[\s.-]*r[\s.-]*t|sort|sorting|ซอส|ซอท|ซอร์ต|ซอร์ท)'
    r'(?:\s*(?:คืออะไร|หมายถึงอะไร|คือ|หมายถึง))?\s*[?!.。！？]*\s*$',
    re.I,
)


def compact(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', text).casefold())


def is_sorting_keyword(query):
    """Recognize a bare sorting term, including common Thai/letter spellings."""
    return bool(SORT_KEYWORD_RE.fullmatch(unicodedata.normalize('NFKC', query).casefold()))


@lru_cache(maxsize=1)
def lexicon():
    path=Path(__file__).resolve().parents[1]/'metadata/semantic_lexicon.json'
    return json.loads(path.read_text()) if path.exists() else {'topics':{},'intents':{}}


@lru_cache(maxsize=1)
def query_examples():
    path=Path(__file__).resolve().parents[1]/'metadata/semantic_queries.json'
    if not path.exists():return {}
    return {compact(r['query']):r for r in json.loads(path.read_text())['examples']}


def plan_query(query):
    normalized = unicodedata.normalize('NFKC', query).casefold()
    if is_sorting_keyword(normalized):
        # In this sorting-only tutor, a standalone "sort" names the general
        # sorting problem rather than an unrelated English meaning.
        normalized = 'sorting'
    # Normalize image-intent words (including common Thai misspellings like รุป)
    normalized = re.sub(r'(?:รุปภาพ|รูปภาพ|รุป|รูป|ภาพ)|\b(?:picture|photo|diagram|illustration|figure)\b', 'diagram', normalized)
    for word in re.findall(r'[a-z]{4,}', normalized):
        match=get_close_matches(word, ['bubble','selection','insertion','merge','counting'],n=1,cutoff=.78)
        if match:
            target=match[0]
            # Outside an explicit "... sort" phrase, accept only one edit.
            # Otherwise real words such as "section" become "selection".
            if len(word)==len(target):
                different=[i for i,(a,b) in enumerate(zip(word,target)) if a!=b]
                one_edit=(len(different)<=1 or (len(different)==2 and different[1]==different[0]+1
                          and word[different[0]]==target[different[1]] and word[different[1]]==target[different[0]]))
            else:
                shorter,longer=sorted((word,target),key=len)
                one_edit=len(longer)-len(shorter)==1 and any(longer[:i]+longer[i+1:]==shorter for i in range(len(longer)))
            if not one_edit and not re.search(r'\b'+re.escape(word)+r'\s+sort\b',normalized):continue
            normalized=re.sub(r'\b'+re.escape(word)+r'\b',match[0],normalized)
    topics=[key for key,values in TOPICS.items() if any(compact(v) in compact(normalized) for v in values+lexicon()['topics'].get(key,[]))]
    if len(topics)>1 and 'principles' in topics:
        topics.remove('principles')
    intent=next((i for i,words in INTENTS.items() if any(compact(w) in compact(normalized) for w in words+lexicon()['intents'].get(i,[]))), 'fact')
    # Mentioning multiple sorting methods in an otherwise plain request implies
    # that the user wants them related or contrasted, even without the literal
    # word "compare" (for example, "bubble กับ selection อันไหนดีกว่า").
    if len(topics)>=2 and intent=='fact':intent='comparison'
    example=query_examples().get(compact(query))
    if example:topics=[example['topic']];intent=example['intent']
    return dict(original=query, normalized=normalized, topics=topics, intent=intent)


def features(text):
    text=compact(text)
    return Counter(text[i:i+3] for i in range(max(0,len(text)-2)))


def cosine(a,b):
    denom=math.sqrt(sum(v*v for v in a.values())*sum(v*v for v in b.values()))
    return sum(v*b.get(k,0) for k,v in a.items())/denom if denom else 0.


def generic_page(query,language='th'):
    plan=plan_query(query)
    if len(plan['topics'])!=1 or plan['intent'] not in ('steps','explanation'):return None
    topic=plan['topics'][0];remaining=compact(plan['normalized'])
    phrases=TOPICS[topic]+lexicon()['topics'].get(topic,[])+INTENTS[plan['intent']]+lexicon()['intents'].get(plan['intent'],[])
    phrases+=['sort','ทำงาน','ได้ไหม','หน่อย','ครับ','ค่ะ','ช่วย','ขอ','สอน','please','does','work','works','is','the']
    for phrase in sorted(phrases,key=len,reverse=True):remaining=remaining.replace(compact(phrase),'')
    if remaining.strip('?!.,: '):return None
    defaults={'steps':{'bubble':38,'selection':47,'insertion':67,'merge':83,'counting':95},
              'explanation':{'bubble':36,'selection':46,'insertion':67,'merge':83,'counting':94}}
    return defaults[plan['intent']].get(topic)


def retrieve(query,data,limit=12,dense_scores=None,section_id=None):
    if data.get('schema_version')==3:
        from .search import hybrid_retrieve
        return hybrid_retrieve(query,data,limit=limit,dense_scores=dense_scores,section_id=section_id)
    raise ValueError('Rebuild the English hierarchical search dataset')
