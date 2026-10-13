# ตรวจหัวข้อและรวมหลักฐานตามหน้า PDF — 13 ตุลาคม 2026

ทำงานในโครงการต่อ ยังไม่จัดหรืออัปเดต ZIP ตามคำสั่งล่าสุดของผู้ใช้ ZIP ที่สร้างไว้ก่อนหน้านี้ไม่ใช่ชุดส่งมอบของสถานะปัจจุบัน

## สิ่งที่แก้

- หน้าอ่านคำตอบรวม Source Text และปุ่มดูหลักฐานให้เหลือหนึ่งชุดต่อเอกสาร/หน้า PDF ที่แสดงในส่วนปัจจุบัน เช่น S2.2 หน้า 37 เหลือปุ่มเดียว ครอบคลุมบรรทัด 3–32 ทั้งหัวข้อ คำอธิบาย และโค้ด
- กรอบไฮไลต์ยังแยกช่วงตามตำแหน่งจริง ไม่ระบายพื้นที่ระหว่างช่วงที่ไม่ได้ใช้ตอบ และไม่รวมข้ามหน้า
- ชื่อหัวข้อที่เป็นประโยคคำถาม เช่น Why sorting? และ What stability guarantees ใช้ exact lookup เมื่อข้อความตรงชื่อในหนังสือ แทนการส่งให้ selector ตีความใหม่ คำถามทั่วไปที่ไม่ตรงชื่อหัวข้อยังใช้เส้นทางเดิม
- การประมาณขนาดตัวอักษรเนื้อหาใช้ตัวอักษรปกติ แยกตัวอักษรในภาพ โค้ด สูตร และตัวเน้นออก ป้องกันข้อความเนื้อหาหน้า 74 ถูกสร้างเป็นหัวข้อย่อยผิด
- Exercises เป็นหัวข้อแม่ของข้อที่มีหมายเลข เช่น 2.2-1 และ 2.2-2 ค้น Exercises แล้วได้ข้อย่อยครบตามลำดับ ส่วนการค้นหมายเลขข้อโดยตรงยังทำได้
- คงการแก้ pagination ที่ให้หัวข้ออยู่ส่วนเดียวกับเนื้อหาที่ตามมา

## ผลตรวจล่าสุด

- Python tests: 114 ผ่านทั้งหมด (`tmp/math_repair/full-tests-final.txt`)
- ชื่อหัวข้อที่มีเนื้อหา: 295/295 ผ่านการค้นตามชื่อจริง แก้กรณีชื่อซ้ำด้วยการเลือก node แล้วตรวจอีกครั้ง ไม่พบหน้าที่มีแต่หัวข้อ
- ตรวจการเลือกหัวข้อชื่อซ้ำ 41 รายการภายในชุดตรวจ โดยไม่ให้เนื้อหาของหัวข้อชื่อเดียวกันต่างตำแหน่งปนกัน
- Parenting: 295/295 ดึง chunk ลูกครบและเรียงตามหนังสือ
- คำถามแนวทาง: 113/113 เส้นทางค้นครอบคลุม target section และ target อยู่ใน candidate pool
- คำถามพื้นฐาน 25 ข้อของทั้งห้าอัลกอริทึม: ตอบจากเนื้อหาของ topic ถูกต้อง ไม่ใช่ชื่อหัวข้ออย่างเดียว
- `The CLRS direction`: ได้ข้อความตัวอย่างที่ผู้ใช้ระบุครบตรงต้นฉบับหน้า 36
- Citation: 857/857 chunks ตรงกับ source offsets; เนื้อหา 4,435/4,435 บรรทัดอยู่ครบ; รูป 48/48 เชื่อม section/page ถูกต้อง
- ข้อมูลปัจจุบัน: 100 หน้า, 857 chunks, 64 sections, 225 subsections, 7 chapter nodes รวม front matter, 844 paragraph nodes
- ตรวจในเบราว์เซอร์จริง: S2.2 แสดงปุ่มหน้า 37 จำนวน 1 ปุ่ม เปิด PDF พร้อมหลักฐานบรรทัด 3–32 ได้ และกลับไปอ่านคำตอบได้

ภาพตรวจอยู่ `tmp/math_repair/page-37-single-evidence-proof.png` และ `tmp/math_repair/page-37-combined-highlight-proof.png`

## ไฟล์หลักที่แก้ในรอบนี้

`app.py`, `ui/evidence_groups.py`, `services/evidence_selection.py`, `services/structure.py`, tests ที่เกี่ยวข้อง, `scripts/audit_heading_display.py` และ metadata/report ที่ rebuild ใหม่ สำรองก่อนแก้ hierarchy ไว้ใน `OLD/hierarchy-display-repair-2026-10-13/before-hierarchy-fix.tar.gz`

PDF ต้นฉบับ, binary รูปภาพ และไฟล์ API key ไม่ถูกแก้ไข Rebuild ใช้ `scripts/rescan.py --language=en --text-only` ส่วน vector status ปรับ fingerprint ตามข้อมูลปัจจุบัน มี embeddings 0/857 ไม่ได้เรียกสร้าง embeddings ในรอบนี้

## ขอบเขตผลตรวจ

ผลด้าน source offsets, parenting และ candidate coverage เป็นการตรวจแบบ deterministic ไม่ใช่ human semantic accuracy หรือคุณภาพคำแปลไทย 100% พบคำแปลที่มีตัวอักษร/ภาษาปนบางช่วงจากโมเดล ซึ่งยังต้องแก้แยกต่างหาก สูตรสองมิติยังต้องตรวจภาพ PDF ประกอบ การรวมปุ่มหลักฐานไม่ได้เปลี่ยนเงื่อนไขการแปลหรือแก้ข้อจำกัดดังกล่าว

ทำซ้ำ:

```bash
./venv/bin/python -m unittest discover -s tests
./venv/bin/python scripts/audit_heading_display.py
./venv/bin/python scripts/audit_algorithm_questions.py
./venv/bin/python scripts/audit_english_search.py
./venv/bin/python scripts/audit_math_repair.py
```
