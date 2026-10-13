# แก้คำตอบหยุดกลางย่อหน้า — 13 ตุลาคม 2026

กรณี “bubble sort” ขาดข้อความหน้า 36 หลังคำว่า intermediate ทำซ้ำได้จาก line-range selection โดยไม่ต้องทำให้ context window เต็ม

## Root Cause

1. Selector คืนเฉพาะ ID และ first_line/last_line ระบบเดิมนำข้อความต้นฉบับมาหั่นตามช่วงนั้นทันที จึงยอมให้ช่วงจบกลางประโยค เช่น p36-l14 ทั้งที่ข้อความต่อยังอยู่ใน p36-l15–16 ไม่ใช่ English text ที่ LLM เขียนจน token หมด
2. definition_rows มี context_spans กำหนดจุดสิ้นสุดตายตัวถึง “right key.” และ “finalized suffix.” ทำให้ fallback ตัดคุณสมบัติและเงื่อนไขท้ายย่อหน้าเช่นกัน อาการนี้เกิดได้เมื่อปิด AI ด้วย

## การแก้

- เอาการตัดด้วยคำปลายทางตายตัวออก ใช้เนื้อหาย่อหน้าของหัวข้อย่อยครบหลังตัดชื่อหัวข้อสำหรับการแสดงคำตอบ
- ช่วงบรรทัดที่ AI เลือกใช้เพื่อระบุย่อหน้า จากนั้นเติมร้อยแก้วให้ครบ source paragraph ด้วย paragraph_id โดยจำกัดอยู่ในเอกสารเดียวกัน รวม continuation chunks/หน้าที่มี paragraph_id เดียวกัน
- ไม่ขยายทั้ง section/chapter ไม่สร้างประโยคใหม่ ทุกช่วงใช้ข้อความตรงตาม char offsets และยังมี Citation แยกหน้าต้นฉบับ
- ตัดรายการซ้ำเมื่อ AI เลือกหลายช่วงของย่อหน้าเดียวกัน คงการตรวจ ID, เลขบรรทัด, ช่วงกลับด้าน, ช่วงซ้ำ และการห้ามตัด code block
- บันทึก selection_completion=complete_source_paragraph เพื่อให้ตรวจได้ว่าใช้การเติมบริบทจากต้นฉบับ

## ผลตรวจ

Regression สำหรับ “bubble sort” ทั้ง fallback และการจำลอง AI เลือกหยุดก่อนท้ายย่อหน้า ได้ “arrays and invariants differ. A trace question must specify the scan direction and what counts as one pass.” ครบ รวม one-inversion property ของ The basic operation

ตรวจ source paragraphs ที่ต่อข้ามหน้าทั้ง 8 กรณี คืนครบทุก continuation chunk และไม่ขยายออกนอก paragraph_id ตรวจ offsets ทุกช่วงตรงกับ page text

เรียก Gemini จริงด้วยคำถาม “bubble sort” รอบล่าสุดได้ selection_state=selected เลือก The CLRS direction และมีท้ายย่อหน้าครบ ผลรายละเอียดอยู่ PARAGRAPH_COMPLETION_LIVE_RESULTS.json การตรวจนี้ยืนยัน source selection ไม่ใช่ผลประเมินความถูกต้องการแปลไทยทุกประโยค

ชุดทดสอบล่าสุด: tmp/math_repair/paragraph-completion-full-tests.txt

ไฟล์หลักที่แก้: services/search.py, services/evidence_selection.py, tests/test_query_recovery.py, tests/test_evidence_selection.py ไม่แก้ PDF, dataset, API key หรือ UI ในรอบนี้ และไม่จัด ZIP

ผลชุดทดสอบรวม: 120 ผ่านทั้งหมด Gemini ในการทดสอบจริงยังเลือก p36-l10–14 แต่ระบบเติมย่อหน้าเดียวกันจนถึง p36-l16 ได้ครบ โดย source offsets ทุกช่วงยังตรง
