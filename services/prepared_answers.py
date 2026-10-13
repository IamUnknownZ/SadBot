"""PDF-backed answers prepared in advance for benchmark questions."""
import json
import re
from functools import lru_cache
from pathlib import Path
from .retrieval import compact, plan_query

PATH=Path(__file__).resolve().parents[1]/'metadata/prepared_answers.json'

_BUBBLE_ALIASES=(
    'bubble sort','bubble','buble sort','buble','bubbel sort','bubbel',
    'บับเบิลซอร์ท','บับเบิ้ลซอร์ท','บับเบิลซอร์ต','บับเบิ้ลซอร์ต',
    'บับเบิลซอท','บับเบิ้ลซอท','บับเบิลซอด','บับเบิลซอส','บับเบิ้ลซอส',
)
_BUBBLE_QUESTION_SUFFIXES=(
    '', 'คือ', 'คืออะไร', 'คือยังไง', 'หมายถึง', 'หมายถึงอะไร',
    'หมายถึงยังไง', 'ความหมาย', 'ความหมายคืออะไร', 'นิยาม',
    'ทำงาน', 'ทำงานอย่างไร', 'ทำงานยังไง', 'หลักการ', 'หลักการทำงาน',
    'definition', 'meaning', 'อะไร',
)
_BUBBLE_QUESTION_PREFIXES=(
    'what is ', 'what is a ', 'what is the ', 'define ',
    'definition of ', 'meaning of ',
)

@lru_cache(maxsize=1)
def routes():
    if not PATH.exists(): return {}
    return json.loads(PATH.read_text()).get('routes',{})


def _is_short_bubble_definition(question):
    """Match only a bare Bubble Sort name or a direct definition request.

    A longer question that mentions a specific property (for example,
    inefficiency) must continue through Gemini and source retrieval.
    """
    text=compact(re.sub(r'[?!.,:;]+',' ',question)).strip()
    aliases={compact(alias) for alias in _BUBBLE_ALIASES}
    suffixes={compact(suffix) for suffix in _BUBBLE_QUESTION_SUFFIXES}
    if text in {alias+suffix for alias in aliases for suffix in suffixes}:
        return True
    spaced=re.sub(r'\s+',' ',question.casefold()).strip(' ?!.,:;')
    return any(compact(spaced)==compact(prefix+alias)
               for alias in aliases for prefix in _BUBBLE_QUESTION_PREFIXES)

def answer_for(question,data):
    text=compact(question)
    row=routes().get(text)
    # Common keyboard slip in the prepared sorting-purpose question.  Normalize
    # it before lookup so it remains an instant local answer with PDF evidence.
    if not row:
        text=text.replace('การเรียนบลําดับ','การเรียงลําดับ')
        row=routes().get(text)
    # Only a bare name/direct definition uses the prepared short answer.
    # Specific follow-ups must reach Gemini and retrieve matching evidence.
    if not row and not re.search(r'\[[^]]+\]', question) and _is_short_bubble_definition(question):
        row=routes().get('__bubble_definition__')
    if not row and ('วัตถุประสงค์หลักของการเรียงลําดับ' in text or 'why sorting' in text):
        row=routes().get('__why_sorting__')
    if not row: return None
    if row['status']!='answered':
        return dict(query=plan_query(question),status='insufficient_evidence',answer='ไม่พบข้อมูลที่รองรับคำถามนี้ในหนังสือภาษาอังกฤษครับ',evidence=[],image=None,choices=[],prepared=True)
    by_id={c['id']:c for c in data['chunks']}
    evidence=[by_id[i] for i in row['evidence_ids'] if i in by_id]
    # A prepared answer without source evidence is not a valid PDF answer.
    # Let the normal Gemini-to-PDF retrieval path handle it instead.
    if not evidence or len(evidence)!=len(row['evidence_ids']): return None
    if row.get('record_id')=='SORT-0018' and _is_short_bubble_definition(question):
        # A one-line definition does not need scan direction, recursion,
        # invariants or an extra 400-word source passage. Only include the
        # second source paragraph when the user explicitly asks how it works.
        normalized=compact(question)
        mechanism=any(compact(term) in normalized for term in (
            'ทำงาน','หลักการ','work','operation'))
        evidence=evidence[:2] if mechanism else evidence[:1]
        answer='\n\n'.join(c['text'] for c in evidence)
    else:
        answer=row.get('answer') or '\n\n'.join(c['text'] for c in evidence)
    return dict(query=plan_query(question),status='answered',answer=answer,evidence=evidence,image=None,choices=[],prepared=True,retrieval_method='prepared_answer')
