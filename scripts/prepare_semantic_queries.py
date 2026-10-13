"""Build transparent query-only examples. These are drafted, not human-labelled data."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SUBJECTS={
 'bubble':['Bubble Sort','บับเบิลซอร์ต','การเรียงแบบฟองสบู่','วิธีสลับตัวข้างกัน','วิธีที่ตัวมากค่อย ๆ ไปท้าย'],
 'selection':['Selection Sort','ซีเล็กชันซอร์ต','การเรียงแบบเลือก','วิธีหาค่าน้อยสุดแล้วสลับ','วิธีเลือกตัวต่ำสุดมาไว้ด้านหน้า'],
 'insertion':['Insertion Sort','อินเซอร์ชันซอร์ต','การเรียงแบบแทรก','วิธีเรียงเหมือนจัดไพ่','วิธีเลื่อนตัวใหญ่แล้วแทรกตัวถัดไป'],
 'merge':['Merge Sort','เมิร์จซอร์ต','การเรียงแบบผสาน','วิธีแบ่งครึ่งแล้วรวม','วิธีเรียกซ้ำแล้วรวมส่วนที่เรียงแล้ว'],
 'counting':['Counting Sort','เคาน์ติงซอร์ต','การเรียงแบบนับ','วิธีนับความถี่แล้วเรียง','วิธีสะสมจำนวนเพื่อหาตำแหน่ง']}
PATTERNS=[
 ('explanation','{s} คืออะไร'),('explanation','{s} ทำงานยังไง'),('explanation','อธิบาย {s} ให้เข้าใจง่ายหน่อย'),('explanation','อยากเข้าใจแนวคิดของ {s}'),
 ('explanation','{s} จัดข้อมูลเข้าที่ได้อย่างไร'),('explanation','{s} มีหลักการอะไร'),('explanation','อธิบายเหตุผลที่ {s} ใช้วิธีนี้'),('explanation','ช่วยเล่าภาพรวมของ {s}'),
 ('steps','สอน {s} ทีละขั้น'),('steps','พาไล่ {s} ทีละรอบได้ไหม'),('steps','{s} เริ่มทำอะไรก่อน'),('steps','ขอตัวอย่าง {s} ตามหนังสือ'),
 ('steps','{s} รอบแรกเกิดอะไรขึ้น'),('steps','{s} ไปขั้นถัดไปยังไง'),('steps','ลองแสดงลำดับขั้นของ {s}'),('steps','อยากเห็นรอบการทำงานของ {s}'),
 ('complexity','{s} ใช้เวลาเท่าไร'),('complexity','{s} ใช้พื้นที่เพิ่มไหม'),('complexity','จำนวนการเปรียบเทียบของ {s} เป็นอย่างไร'),('complexity','กรณีแย่สุดของ {s} ใช้เวลายังไง'),
 ('complexity','กรณีข้อมูลเรียงแล้วของ {s} ใช้เวลายังไง'),('complexity','{s} กินแรมแค่ไหน'),('stability','{s} เสถียรไหม'),('stability','{s} รักษาลำดับคีย์ที่เท่ากันอย่างไร'),
 ('stability','คีย์ซ้ำใน {s} จะมีลำดับเดิมไหม'),('stability','ทำไมต้องสนใจความเสถียรใน {s}'),('code','ขอดูรหัสเทียมของ {s} จากหนังสือ'),('code','{s} เขียนขั้นตอนเป็นโค้ดยังไง'),
 ('code','อธิบายตัวแปรในรหัสเทียม {s}'),('code','ขอหลักฐานโค้ดของ {s} ที่อยู่ใน PDF')]
PREFIXES=['','ถามหน่อยนะ ', 'กำลังอ่านอยู่ อยากรู้ว่า ', 'ยังงงตรงนี้ ', 'ช่วยดูให้ที ', 'ขอถามจากหนังสือว่า ', 'ก่อนพรีเซนต์อยากทบทวน ', 'ขอแบบตามต้นฉบับนะ ', 'กำลังหัดเรียนเรื่องนี้ ', 'ขอให้ช่วยอธิบายหน่อย ']
# 5 algorithms x 5 topic descriptions x 30 question purposes x 2 tones = 1,500 examples.
examples=[]
for topic,subjects in SUBJECTS.items():
 for subject in subjects:
  for i,(intent,pattern) in enumerate(PATTERNS):
   for prefix in [PREFIXES[0],PREFIXES[1+(i%9)]]:
    examples.append(dict(query=prefix+pattern.format(s=subject),topic=topic,intent=intent))
assert len(examples)==1500 and len({r['query'] for r in examples})==1500
value=dict(schema_version=1,origin='AI-drafted natural-language query patterns; not collected from real users',human_review_required=True,
    purpose='Query routing only. Contains no factual answers, no user records, and no training results.',count=len(examples),examples=examples)
(ROOT/'metadata/semantic_queries.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
print('Prepared 1,500 unique query-only examples')
