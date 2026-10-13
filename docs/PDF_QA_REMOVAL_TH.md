# ลบ Semantic questions and answers จาก PDF จริง — 13 ตุลาคม 2026

ลบหัวข้อและบล็อก Q&A 39 จุด รวม 113 คู่ จาก PDF ที่ Runtime ใช้จริง โดยไม่ reflow ไม่เปลี่ยนจำนวนหน้า ไม่เลื่อนรูปหรือข้อความอื่น และไม่เติมข้อความใหม่ในช่องที่ลบ การทำครั้งนี้ใช้ text redaction และบันทึก PDF ใหม่พร้อม garbage collection ไม่ใช่การวางสีขาวปิดข้อความที่ยังค้นหาได้

## ต้นฉบับและข้อมูลที่เก็บไว้

- PDF ปัจจุบัน: `book_data/Cormen_Basic_Sorting_100_Pages.pdf`
- PDF ก่อนแก้: `OLD/pdf-qa-removal-2026-10-13/source-before-removal.pdf`
- Q&A ครบทั้ง 113 คู่ พร้อมหน้าและพิกัด: `OLD/pdf-qa-removal-2026-10-13/removed-qa-reference.json`
- คำถามสำหรับช่วยค้น: `metadata/reviewed_query_routes.json` มีเฉพาะคำถามและหัวข้อเป้าหมาย ไม่มีคำตอบ โดยผูกกับ SHA-256 ของ PDF ปัจจุบัน

บริการ ingest แปลงหัวข้อเป้าหมายเป็น ID ใหม่หลัง rebuild และตรวจว่าตรงกับ section/page เพียงแห่งเดียว ข้อมูลเก็บนอก Runtime ไม่ใช่แหล่งคำตอบหรือ embedding ส่วน synthetic-Q&A filter เดิมยังอยู่เพื่อป้องกันการนำบล็อกชนิดนี้กลับเข้ามาในอนาคต

## ผลตรวจ PDF

ตรวจครบ 100 หน้า จำนวนหน้า/MediaBox/CropBox/rotation/bookmarks เหมือนเดิม คำที่ไม่ลบ 34,720 คำอยู่พิกัดเดิมทุกคำ (coordinate delta 0.0 จุด) เปรียบเทียบภาพทุกหน้า พบพิกเซลเปลี่ยนนอกขอบเขต Q&A จำนวน 0 พิกเซล ตรวจภาพรวมก่อน/หลังของทั้ง 39 หน้าที่แก้แล้ว และตรวจหน้า 39 แบบเต็มหน้า

ไฟล์ผลตรวจ: `docs/PDF_QA_REMOVAL_RESULTS.json` ภาพเทียบอยู่ `tmp/pdfs/qa-removal/` พื้นที่ที่ลบว่างตามขนาดเดิม รูปและคำบรรยายยังอยู่ตำแหน่งเดิม

## ผลต่อ Runtime

Rebuild แบบ text-only โดยเก็บ binary รูปเดิมครบ 48 รูป อัปเดต source hash ของ math glyph map หลังตรวจ font streams ว่าเหมือนเดิม และอัปเดต figure review provenance หลังพิสูจน์ว่าพิกเซลนอก Q&A ไม่เปลี่ยน จึงไม่ปิดการกู้สัญลักษณ์คณิตศาสตร์เดิม

ได้ 868 chunks และคงคำถามแนวทาง 113 ข้อ การเพิ่มจาก 857 เป็น 868 ไม่ใช่การแต่งข้อมูลเพิ่ม แต่เป็นป้ายข้อความในรูป 11 chunks ที่ filter เดิมเคยกันรวมไปกับ Q&A แล้วได้รับการคืนเข้าดัชนีจาก PDF จริง กรอบลบครั้งนี้ใช้ text block ของ Q&A จริงจึงไม่ลบป้ายในรูป

ตรวจหัวข้อ 295/295 และเส้นทางคำถาม 113/113 ผ่าน รายงานค้นและ Citation ล่าสุดอยู่ `docs/ENGLISH_SEARCH_RESULTS.json` ชุดทดสอบรอบนี้อยู่ `tmp/pdfs/qa-removal-full-tests.txt`

Vector fingerprint ถูกปรับตาม source/dataset ใหม่ ไม่ใช้ embeddings เดิมและไม่ได้เรียกสร้าง embeddings ผ่าน API ในรอบนี้ ประวัติแชตใน session จะเริ่มใหม่เมื่อ dataset revision เปลี่ยน เพื่อป้องกัน Citation จาก PDF เวอร์ชันก่อนหน้า

ไฟล์ที่แก้: PDF ปัจจุบัน, `services/ingest.py`, `metadata/reviewed_query_routes.json`, math/figure provenance และ metadata จาก rebuild เพิ่ม utility `scripts/remove_pdf_editor_qa.py` กับ tests ที่เกี่ยวข้อง UI และ API key ไม่ถูกแก้ ไม่มีการจัดหรืออัปเดต ZIP
