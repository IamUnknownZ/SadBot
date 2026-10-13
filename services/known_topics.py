"""Fast, source-backed routes for familiar course-topic names.

These aliases are copied and narrowed from the former Thai query lexicon.  They
only point to headings that exist in the current English PDF dataset.
"""
from __future__ import annotations

import re
from .retrieval import compact

# A bare course-topic name should never need an API round trip.  ``section_id``
# is used only where the book has a named parent with useful child paragraphs.
TOPICS = (
    {
        'canonical': 'Algorithms',
        'section_id': 'book-en-section-0053',
        'aliases': (
            'algorithm', 'algorithms', 'อัลกอริทึม', 'อัลกอริทึ่ม',
            'อัลกอลิทึม', 'อัลกอริทึมส์',
        ),
    },
    {
        'canonical': 'sorting',
        'section_id': None,
        'aliases': (
            'sort', 'sorting', 'sort algorithm', 'sorting algorithm',
            'การเรียงลำดับ', 'การเรียงลำดับข้อมูล', 'เรียงลำดับ',
            'เรียงข้อมูล', 'ซอร์ท', 'ซอท', 'ซอร์ต', 'ซอส',
        ),
    },
    {
        'canonical': 'bubble sort',
        'section_id': None,
        'aliases': (
            'bubble', 'bubble sort', 'bubble sorting', 'buble', 'buble sort',
            'bubbel', 'bubbel sort', 'buble sord', 'บับเบิลซอร์ท', 'บับเบิ้ลซอร์ท',
            'บับเบิลซอร์ต', 'บับเบิ้ลซอร์ต', 'บับเบิลซอท', 'บับเบิ้ลซอท',
            'บับเบิลซอด', 'บับเบิล ซอร์ท', 'บับเบิ้ล ซอร์ท',
            'เรียงแบบฟองสบู่', 'ฟองสบู่', 'การเรียงแบบฟองสบู่',
            'การเรียงแบบฟอง', 'เรียงลำดับแบบฟอง', 'แบบฟอง',
        ),
    },
    {
        'canonical': 'selection sort',
        'section_id': None,
        'aliases': (
            'selection', 'selection sort', 'selection sorting', 'select sort',
            'seletion sort', 'selction sort', 'secletion sort',
            'ซีเล็กชันซอร์ท', 'ซีเล็กชั่นซอร์ท', 'ซีเลคชันซอร์ท',
            'ซีเลคชั่นซอร์ท', 'เซเล็กชันซอร์ท', 'เซเล็กชั่นซอร์ท',
            'ซีเล็กชันซอท', 'ซีเล็กชั่นซอท', 'การเรียงแบบเลือก',
            'เรียงแบบเลือก', 'เลือกค่าน้อยสุด', 'เลือกค่าต่ำสุด', 'แบบเลือก',
        ),
    },
    {
        'canonical': 'insertion sort',
        'section_id': None,
        'aliases': (
            'insertion', 'insertion sort', 'insertion sorting', 'insert sort',
            'instertion sort', 'inserton sort', 'insertions sort',
            'อินเซอร์ชันซอร์ท', 'อินเซิร์ชันซอร์ท', 'อินเซอชันซอร์ท',
            'อินเซอชั่นซอร์ท', 'อินเซอร์ชั่นซอร์ท', 'อินเซิร์ชั่นซอร์ท',
            'อินเซอร์ชันซอท', 'อินเซิร์ชันซอท', 'การเรียงแบบแทรก',
            'เรียงแบบแทรก', 'แทรกข้อมูลเรียงลำดับ', 'แบบแทรก',
        ),
    },
    {
        'canonical': 'merge sort',
        'section_id': None,
        'aliases': (
            'merge', 'merge sort', 'merge sorting', 'merg sort', 'marge sort',
            'merch sort', 'เมิร์จซอร์ท',
            'เมอร์จซอร์ท', 'เมิร์กซอร์ท', 'เมิจก์ซอร์ท', 'เมิร์จซอท',
            'เมอร์จซอท', 'การเรียงแบบผสาน', 'เรียงแบบผสาน',
            'การเรียงแบบรวม', 'แบ่งแล้วรวม', 'แบ่งครึ่งแล้วรวม', 'แบบผสาน',
        ),
    },
    {
        'canonical': 'counting sort',
        'section_id': None,
        'aliases': (
            'counting', 'counting sort', 'counting sorting', 'count sort',
            'couting sort', 'countin sort', 'conuting sort',
            'เคาน์ติ้งซอร์ท', 'เคาน์ทิงซอร์ท', 'เคาน์ติ้งซอท',
            'เคาท์ติ้งซอร์ท', 'เคาน์ทิงซอท', 'เคาน์ติ้ง ซอร์ท',
            'เคาน์ทิง ซอร์ท', 'การเรียงแบบนับ', 'เรียงแบบนับ',
            'เรียงด้วยการนับ', 'นับความถี่แล้วเรียง', 'วิธีนับจำนวน',
            'อัลกอริทึมนับ', 'แบบนับ',
        ),
    },
)

# Natural Thai wrappers are removed only for a whole known-topic request.  A
# question with a separate intent such as "เวลา" still goes through Gemini.
_SUFFIXES = tuple(compact(value) for value in (
    'คืออะไร', 'หมายถึงอะไร', 'ความหมายคืออะไร', 'นิยามคืออะไร',
    'คือ', 'อธิบาย', 'อธิบายหน่อย', 'หน่อย', 'ครับ', 'ค่ะ', 'คะ',
))
_PREFIXES = tuple(compact(value) for value in ('ช่วยอธิบาย', 'ขออธิบาย', 'เรื่อง', 'หัวข้อ'))


def _bare_topic(question: str) -> str:
    text = compact(question).strip('?!.,:;')
    changed = True
    while changed:
        changed = False
        for prefix in _PREFIXES:
            if text.startswith(prefix):
                text = text[len(prefix):]
                changed = True
        for suffix in _SUFFIXES:
            if text.endswith(suffix):
                text = text[:-len(suffix)]
                changed = True
    return text.strip('?!.,:;')


def known_topic(question: str):
    """Return a current-PDF route for a bare Thai or English topic name."""
    bare = _bare_topic(question)
    if not bare:
        return None
    for topic in TOPICS:
        if bare in {compact(alias) for alias in topic['aliases']}:
            return topic
    return None
