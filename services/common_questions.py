"""Conservative source-only routes for unambiguous beginner sorting questions.

Only returns source chunk IDs, never an answer drafted from background knowledge.
Novel, qualified or ambiguous questions still go through Gemini evidence selection.
"""
import re

from .retrieval import plan_query
from .search import normalize

INTRO = {
    'bubble': ('p34-c0344', 'p36-c0370'),
    'selection': ('p46-c0492',),
    'insertion': ('p55-c0598',),
    'merge': ('p72-c0759', 'p72-c0760', 'p72-c0761', 'p72-c0762'),
    'counting': ('p90-c0970', 'p90-c0971'),
}
TIME = {
    'bubble': ('p40-c0415', 'p40-c0419'),
    'selection': ('p49-c0527',),
    'insertion': ('p68-c0710',),
    'merge': ('p78-c0826',),
    'counting': ('p92-c0989',),
}
STABILITY = {
    'bubble': ('p41-c0427',),
    'selection': ('p50-c0539', 'p50-c0541'),
    'insertion': ('p69-c0720',),
    'merge': ('p87-c0925',),
    'counting': ('p92-c0991',),
}
SPACE = {
    'bubble': ('p43-c0452',),
    'selection': ('p51-c0555',),
    'merge': ('p85-c0906',),
    'counting': ('p97-c1049',),
}
NAMES = {
    'bubble': ('bubble sort', 'bubble sorting', 'bubble', 'บับเบิลซอร์ท', 'บับเบิ้ลซอร์ท'),
    'selection': ('selection sort', 'selection sorting', 'selection', 'ซีเล็กชันซอร์ท', 'ซีเล็กชั่นซอร์ท'),
    'insertion': ('insertion sort', 'insertion sorting', 'insertion', 'อินเซอร์ชันซอร์ท', 'อินเซิร์ชันซอร์ท'),
    'merge': ('merge sort', 'merge sorting', 'merge', 'เมิร์จซอร์ท', 'เมอร์จซอร์ท'),
    'counting': ('counting sort', 'counting sorting', 'counting', 'เคาน์ติ้งซอร์ท', 'เคาน์ทิงซอร์ท'),
}
QUESTION_WORDS = re.compile(
    r'^(?:what (?:is|are) (?:a |an |the )?|define |explain |describe |'
    r'how (?:does|do) |(?:ขอ|ช่วย|กรุณา)?(?:อธิบาย|นิยาม|สรุป|เรื่อง|เกี่ยวกับ)\s*)',
    re.I,
)


def _topic_and_remainder(question):
    q=normalize(question).strip(' \t\n?!.,。！？')
    present=[]
    for topic,aliases in NAMES.items():
        for alias in sorted(aliases,key=len,reverse=True):
            alias=normalize(alias)
            if re.search(r'(?<![a-z])'+re.escape(alias)+r'(?![a-z])',q):
                present.append(topic)
                q=re.sub(r'(?<![a-z])'+re.escape(alias)+r'(?![a-z])',' ',q,count=1)
                break
    return present, ' '.join(q.split())


def _clear_simple(question,topics):
    if not topics or re.search(r'\d|\[[^]]*\]|[<>]|\b(?:not|except|if|given|with|without|why|when|which)\b',question,re.I):
        return False
    return True


def source_ids_for(question):
    """Choose only a bounded, explicitly named question family."""
    normalized=normalize(question)
    q=normalized.strip(' ?!.,。！？')
    if q in {normalize(x) for x in ('what is sorting','what is sorting algorithm','การเรียงลำดับคืออะไร')}:
        return ('p5-c0047','p5-c0048','p5-c0049')
    if q in {normalize(x) for x in ('what is an algorithm','what are algorithms','อัลกอริทึมหมายถึงอะไร','อัลกอริทึมคืออะไร')}:
        return ('p5-c0045','p5-c0046')
    if q in {normalize(x) for x in ('ทำไมต้องเรียงลำดับ','why do we sort','why is sorting important')}:
        return ('p10-c0083','p10-c0084')
    if q in {normalize(x) for x in ('what is big o','what is big-o','big o คืออะไร','big o หมายถึงอะไร')}:
        return ('p20-c0171',)
    if q in {normalize(x) for x in ('what is time complexity','time complexity คืออะไร','ความซับซ้อนด้านเวลาคืออะไร')}:
        return ('p61-c0655','p63-c0666')
    if q in {normalize(x) for x in ('what is stability in sorting','what is stable sorting','stable sort คืออะไร','การเรียงแบบเสถียรคืออะไร')}:
        return ('p27-c0255',)
    if q in {normalize(x) for x in ('what is auxiliary space','auxiliary space คืออะไร','หน่วยความจำเพิ่มเติมคืออะไร')}:
        return ('p28-c0269',)
    if q in {normalize(x) for x in ('what is divide and conquer','divide and conquer คืออะไร','แบ่งแยกและเอาชนะคืออะไร')}:
        return ('p72-c0755','p72-c0756','p72-c0757','p72-c0758')
    # Numeric-looking strings use their comparator's ordering, which can
    # differ from numeric value ordering. The reviewed source gives the exact
    # "10" versus "2" example, so this family does not need Gemini routing.
    numeric_string_cues=('numeric string','number string','strings','string order','lexicographic',
                         'สตริง','ข้อความ','ตัวเลขแบบข้อความ')
    ordering_cues=('sort','order','differ','compare','เรียง','ลำดับ','ต่าง','เปรียบเทียบ')
    if ('10' in q and '2' in q and any(cue in q for cue in numeric_string_cues)
        and any(cue in q for cue in ordering_cues)):
        return ('p26-c0246',)
    if q in {normalize(x) for x in ('what makes an algorithm correct','what is algorithm correctness','ความถูกต้องของอัลกอริทึมคืออะไร')}:
        return ('p6-c0051',)
    if q in {normalize(x) for x in ('what is big theta','what is theta notation','theta notation คืออะไร')}:
        return ('p17-c0150',)
    if q in {normalize(x) for x in ('what is big omega','what is omega notation','omega notation คืออะไร')}:
        return ('p21-c0182',)
    if q in {normalize(x) for x in ('what is an inversion in sorting','what is an inversion','inversion คืออะไร')}:
        return ('p40-c0417',)
    if q in {normalize(x) for x in ('which sorting algorithm is best','ควรใช้อัลกอริทึมเรียงลำดับตัวไหนดี')}:
        return ('p33-c0326',)
    # Explicit notation-versus-input-case misconception: match narrowly so
    # added algorithms, array examples or qualifications still get interpreted.
    if q in {normalize(x).strip(' ?!.,。！？') for x in (
        'Do Big-O, Omega, and Theta notation identify best, worst, or average cases by themselves?',
        'Do Big O, Omega and Theta represent best, worst and average cases?',
        'Big-O, Omega, Theta ต่างกับ best worst average case อย่างไร',
    )}:
        return ('p29-c0278',)
    # Check prerequisites before choosing counting sort: the book explicitly
    # requires integer keys and a manageable range. Keep this route exact so
    # qualified questions still require evidence tailored to their conditions.
    if q in {normalize(x).strip(' ?!.,。！？') for x in (
        'What should we check before using counting sort?',
        'What should I check before choosing counting sort?',
        'ก่อนใช้ Counting Sort ควรตรวจสอบอะไรบ้าง',
    )}:
        return ('p90-c0970','p94-c1009','p94-c1013','p97-c1047')
    topics,remainder=_topic_and_remainder(question)
    if not _clear_simple(normalized,topics):return None
    if len(topics)==2 and plan_query(question)['intent']=='comparison':
        # Pure pair-comparison only: no new array, conditions, worked example,
        # restrictions or complexity-specific comparison.
        rest=re.sub(r'\b(?:compare|comparison|vs|versus|and|with|between|difference|different)\b', ' ',remainder)
        for word in ('เปรียบเทียบ','ความแตกต่าง','ต่างกันอย่างไร','ต่างกันยังไง','กับ','และ','ระหว่าง','เทียบ'):
            rest=rest.replace(word,' ')
        if rest.strip():return None
        a,b=topics
        # One introductory explanation and one running-time source per method.
        return (*INTRO[a][:1],*TIME[a][:1],*INTRO[b][:1],*TIME[b][:1])
    if len(topics)!=1:return None
    topic=topics[0]
    r=remainder.strip(' ?!.,。！？')
    # Drop only truly generic request wrappers and keep qualifiers authoritative.
    r=QUESTION_WORDS.sub('',r).strip()
    for phrase in ('what is','what are','how does','is', 'คืออะไร','หมายถึงอะไร','หมายถึง','คือ','ทำงานอย่างไร','ทำงานยังไง','มีหลักการทำงานอย่างไร','works','work','algorithm','algorithms','หลักการทำงาน','การทำงาน','อธิบายการทำงาน','นิยาม','ความหมาย','how it works','how does it work'):
        phrase=normalize(phrase)
        if r==phrase or r==('it '+phrase):
            return INTRO[topic]
    if not r:return INTRO[topic]
    if r in {normalize(s) for s in ('time complexity','complexity','running time','best case','worst case','ความซับซ้อน','ความซับซ้อนด้านเวลา','ความซับซ้อนเวลา','ใช้เวลากี่','ใช้เวลาเท่าไร')}:
        return TIME[topic]
    if r in {normalize(s) for s in ('stability','stable','is stable','stable or unstable','เสถียรไหม','เสถียรหรือไม่','มีเสถียรภาพไหม','ความเสถียร','เสถียร')}:
        return STABILITY[topic]
    if r in {normalize(s) for s in ('space complexity','auxiliary space','space','memory','ใช้หน่วยความจำเท่าไร','ความซับซ้อนด้านพื้นที่','ใช้พื้นที่เท่าไร')}:
        return SPACE.get(topic)
    return None


def source_evidence(question,data):
    ids=source_ids_for(question)
    if not ids:return None
    indexed={c['id']:c for c in data.get('chunks',[])}
    if any(ident not in indexed for ident in ids):return None
    rows=[indexed[ident] for ident in ids]
    if any(not c.get('text') or c.get('kind') not in ('paragraph','list')
           or c['text']!=data['pages'][c['page']-1]['text'][c['char_start']:c['char_end']]
           for c in rows):return None
    return [dict(c,retrieval_method='common_source_question') for c in sorted(rows,key=lambda c:c['order'])]
