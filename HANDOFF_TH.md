# Sorty — คู่มือส่งต่องาน วันที่ 13 ตุลาคม 2026

## เริ่มอ่านตรงนี้

### สถานะ Runtime ปัจจุบัน — อัปเดตวันที่ 13 ตุลาคม 2026

คำถามไม่จำเป็นต้องเข้า Gemini ทุกครั้ง ระบบตรวจเส้นทางที่รู้จักในเครื่องก่อน แล้วใช้ Gemini เมื่อเป็นคำถามใหม่หรือจำเป็นต้องตีความภาษามนุษย์

- ลำดับปัจจุบัน: small talk → prepared answer → known negative → known topic → exact heading → Gemini question routing
- ชื่ออัลกอริทึมตรง ๆ และคำถามที่เตรียมไว้ตอบได้เร็วโดยไม่รอ API
- คำถามใหม่ส่งเข้า `services.question_routing.interpret_question` แล้ว Gemini คืนเฉพาะ `mode`, `search_query`, `section_id`
- ขั้นเลือกหลักฐานรับได้เฉพาะ source IDs และช่วงบรรทัดที่ระบบส่งให้ โมเดลไม่ได้เขียนข้อเท็จจริงแทนหนังสือ
- โมเดลถูกตรึงใน `app.py` เป็น `gemini-3.1-flash-lite`; ค่า `GEMINI_MODEL` ใน `.env` หรือ Secrets ไม่เปลี่ยนรุ่น
- ตีความและเลือกหลักฐานใช้ `max_output_tokens=300`; แปลใช้ `1,800`; `temperature=0`; Flash Lite ใช้ `thinking_level="minimal"` ซึ่งเป็นระดับต่ำสุดที่ Gemini 3.1 รองรับ
- Timeout คือ `120,000 ms` ต่อคำขอ ขั้นตีความ/เลือกหลักฐานลองสูงสุด 2 ครั้งต่อ key เมื่อได้ 429/500/502/503/504 ส่วนการแปลลอง 1 ครั้งต่อ key
- หากมี key สำรอง ระบบลอง key สำรองหลัง key หลักใช้ไม่ได้ จึงอาจมีเวลารอรวมมากกว่าค่า timeout ของคำขอเดียว
- หาก routing ได้ 500/503/504 หลังลอง API แล้ว ระบบใช้ exact heading, aliases และ BM25 ในเครื่องเป็น fallback โดยยังตอบจาก PDF เท่านั้น ถ้าหาหลักฐานไม่ได้จึงแสดงข้อผิดพลาด routing
- การแปลใช้คำแปลที่ตรวจเองก่อน ปัจจุบันมี Selection Sort ที่ผูกกับข้อความอังกฤษต้นฉบับ ส่วนอื่นใช้ Gemini หากแปลไม่สำเร็จจะแสดงอังกฤษ
- PDF ภาษาไทยเก่าใน `OLD/` ไม่ได้ใช้เป็น Runtime เพราะข้อความถูกแยกคำและตัดย่อหน้าไม่เหมาะกับการอ่าน
- Dataset ปัจจุบันมี 100 หน้า, 868 chunks, 48 รูป และ query guidance 113 รายการ
- Embedding index ยังไม่พร้อม: `0/868`; ระบบยังใช้ exact heading, aliases, keyword/BM25 และ Gemini selection ได้

Commit ที่รวมการแก้คำแปลล่าสุดคือ `8c03804` ก่อนส่งงานให้ตรวจ `git status`, remote และ deployment revision อีกครั้ง

หัวข้อถัดไปบางส่วนบันทึกประวัติการแก้ก่อน Dataset รุ่นปัจจุบัน ตัวเลขสถานะล่าสุดให้ยึดหัวข้อนี้เป็นหลัก

Sorty เป็น Streamlit chatbot เรื่อง sorting algorithms รับคำถามไทย/อังกฤษ ค้นหลักฐานจาก PDF ภาษาอังกฤษ แล้วใช้ Gemini เลือกช่วงหลักฐานและแปลเป็นไทย ไม่ใช้ฐานข้อมูลผู้ใช้ ไม่มีบัญชีผู้ใช้ และไม่เก็บบทสนทนาแบบถาวร มีประวัติระหว่าง session เท่านั้น

Runtime ใช้ `book_data/Cormen_Basic_Sorting_100_Pages.pdf` 100 หน้าเพียงไฟล์เดียว เป็นเอกสารรวมข้อความ CLRS กับ supplements ที่ติดป้ายไว้ ไม่ควรอ้างว่า supplements ทั้งหมดเป็นข้อความดั้งเดิมของ CLRS ไฟล์แปลไทยอยู่ใน OLD เพื่ออ้างอิงนอก runtime เท่านั้น ห้ามนำกลับมาสร้างคำตอบหรือ index โดยไม่ได้ตกลงเปลี่ยนข้อกำหนด

ชุดส่งมอบรวม source, dataset ที่สร้างใหม่, รูปภาพ, PDF.js, tests, เอกสาร, OLD และ Python environment เดิม ไม่มี API key จริง ไม่ต้อง npm install เพื่อใช้แอป ตรวจ `PACKAGE_MANIFEST.json`, `PACKAGE_EXCLUSIONS.json` และ `PACKAGE_VERIFICATION.json` ที่ราก ZIP สำหรับรายการจริงและผลตรวจ ประวัติ Git ในชุดส่งมอบเป็นสำเนาที่ล้าง credential แล้ว (commit refs เก็บเป็น Git; tree refs ภายในของเครื่องมือเก็บเป็น snapshot ใน GIT_EXTRA_REFS.json) จึงมี commit hash บางส่วนเปลี่ยน อ่าน GIT_HANDOFF ก่อนนำไป push

## ตั้งค่าเครื่องใหม่

แนะนำ Python 3.12 และเปิด terminal ในโฟลเดอร์โครงการหลังแตก ZIP Python environment เดิมแนบไว้เพื่อให้ไฟล์ครบ แต่มี binary และ path ของ Linux เครื่องต้นทาง ไม่ควรย้ายไปใช้ตรง ๆ บน Windows หรือเครื่องอื่น ให้เปลี่ยนชื่อ `venv` เดิมก่อนแล้วสร้างใหม่

Linux/macOS:

```bash
mv venv venv-original-machine
python3 -m venv venv
./venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
./venv/bin/python -m streamlit run app.py --server.port 8502
```

Windows PowerShell:

```powershell
Rename-Item venv venv-original-machine
py -3.12 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\venv\Scripts\python.exe -m streamlit run app.py --server.port 8502
```

ใส่ key ของผู้รับเองใน `.env` ช่อง `GEMINI_API_KEY` และ `GEMINI_API_KEY_FALLBACK` ห้าม commit ไฟล์นี้ รุ่นข้อความถูกตรึงใน `app.py` เป็น `gemini-3.1-flash-lite`; `GEMINI_MODEL` ในไฟล์ตั้งค่าไม่มีผลต่อ Runtime ปัจจุบัน `requirements-handoff-lock.txt` บันทึกเวอร์ชันจากเครื่องต้นทาง ส่วน `requirements.txt` เป็นข้อกำหนดติดตั้งหลัก

เปิด `http://localhost:8502` บนเครื่องเดียวกัน Linux มี `./run.sh` ซึ่งใช้ venv เดิมและผูกกับ 127.0.0.1 พอร์ต 8502 หากพอร์ตชนให้เปลี่ยนพอร์ตในคำสั่งเริ่ม ไม่ต้องมี Node, npm, database หรือบริการ backend เพิ่มเพื่อเปิดแอป

## โครงสร้างและเส้นทางข้อมูล

- `app.py`: หน้าจอ Streamlit, session, การเรียกค้นและแปล, ปุ่มดูหลักฐาน
- `services/ingest.py`: อ่าน PDF, สร้าง Document > Chapter > Section > Subsection > Paragraph, offsets และพิกัด
- `services/math_repair.py` และ `metadata/math_glyph_map.json`: กู้ glyph คณิตศาสตร์เฉพาะ PDF/font ที่ hash ตรง
- `services/search.py`, `services/retrieval.py`: normalize คำถาม, แก้ typo แบบจำกัด, exact heading, keyword/BM25 และ optional vector scores
- `services/evidence_selection.py`: ส่ง candidate ที่จำกัดขนาดให้ LLM เลือกเฉพาะ ID และช่วงบรรทัด ตรวจ ID/offset ก่อนรับผล
- `services/answering.py`: ประกอบหลักฐาน ควบคุม direct lookup/fallback และรูปประกอบ
- `services/translation.py`: แปล/จัดข้อความจากหลักฐาน ป้องกันตัวเลข สูตร โค้ด และปฏิเสธผลตรวจไม่ผ่าน
- `ui/reading_view.py`: แสดงข้อความ/โค้ด; `ui/evidence_groups.py`: รวมหลักฐานที่ต่อกัน; `ui/document_viewer.py`, `ui/pdf_viewer/`: เปิด PDF และ highlight ตามพิกัด
- `metadata/`: dataset, hierarchy, keyword index, figure links และ provenance; `assets/`: รูปที่คัดตรวจแล้ว
- `vector_store/`: สถานะ embedding; `scripts/`: rebuild/audit; `tests/`: regression tests
- `OLD/`: ข้อมูลเก่าและ backup ห้ามใช้แทน runtime; `tmp/`: หลักฐานการตรวจและบันทึกทดลอง ไม่ใช่ข้อมูลคำตอบ

LLM เลือกหลักฐานโดยตอบ JSON ไม่ได้เขียนข้อเท็จจริงใหม่ในขั้นเลือก การแปลเป็นอีกขั้นหนึ่ง ข้อความ Source Text ยังคงอังกฤษที่ค้นพบ ส่วนข้อความดิบก่อนกู้ glyph เก็บใน `raw_text` ของบรรทัดและ spans นโยบายนี้ไม่ใช่หลักประกันว่าการแปล LLM ถูกต้อง 100% ต้องมีผู้ตรวจภาษา/ความหมายเพิ่มสำหรับการรายงานผลวิจัย

## การเปลี่ยนแปลงรอบล่าสุดและ Root Cause

1. ฟอนต์คณิตศาสตร์ฝังใน PDF มี text mapping ผิด เช่น `D` ในฟอนต์หนึ่งจริง ๆ เป็น `=` และ `‚` เป็น `Θ` การแทนตัวอักษรทั่วทั้งเล่มจะทำให้ข้อความธรรมดาเสีย จึงตรวจภาพ glyph atlas แล้วทำ mapping ตาม font + glyph ID ผูกกับ SHA-256 ของ PDF และฟอนต์เท่านั้น ใช้ตำแหน่งของ span กู้ script ที่ระบุได้ เก็บข้อความดิบและพิกัดไว้ครบ ไม่ใช้ LLM เดาสูตร
2. Exact heading ที่ขึ้นต้น `S6.7` หลุดหลังคำถามถูกแปลงเป็นตัวพิมพ์เล็ก เพราะ regex เดิมรองรับเฉพาะ S ตัวใหญ่ ส่งผลให้ไปค้น candidate ทั่วไปและได้ Merge sort ปน แก้ regex ให้ไม่ขึ้นกับตัวพิมพ์ เพิ่ม regression ทั้ง S6.7/s6.7 และห้ามเรียก selector ในการทดสอบนี้ ต้องได้เฉพาะหน้า 100
3. ประวัติรอบกู้ข้อความเคยทำให้จำนวน chunks เปลี่ยนหลายครั้ง ปัจจุบันต้องยึด `metadata/dataset.json` ซึ่งมี 868 chunks และไม่ใช้ vector revision เก่าที่สร้างจากข้อความหรือ IDs คนละชุด

ไฟล์ production ที่แก้ในรอบนี้: `services/ingest.py`, `services/math_repair.py` (ใหม่), `services/search.py`, `scripts/rescan.py` และ math glyph map รวมถึง metadata ที่ rebuild รายการละเอียดและสรุป audit อยู่ `docs/MATH_REPAIR_RESULTS.json` ไม่เปลี่ยน UI, API key, source PDF หรือ binary รูปภาพ

## สถานะข้อมูลและผลตรวจ

Dataset ปัจจุบันมี 100 หน้า, 868 chunks, 64 sections, 225 subsections, 7 chapter nodes, 855 paragraph nodes และ 48 รูปที่ตรวจแล้ว ตัวเลขนี้อ่านจาก `metadata/dataset.json` รอบล่าสุด ส่วนผลกู้ glyph ในรายงานเดิมเป็นประวัติของขั้น rebuild และไม่ควรใช้แทนจำนวนโครงสร้างปัจจุบัน

ดู `docs/ENGLISH_SEARCH_RESULTS.json` สำหรับผลค้น 16 คำถาม, exact heading/parent-child coverage, citation offsets, body-line coverage และ image links; `docs/MATH_REPAIR_RESULTS.json` สำหรับความคงเดิมของต้นฉบับ, จำนวนซ่อม และกรณี S6.7 ผลทดสอบ Python อยู่ `tmp/math_repair/full-tests-final.txt` รายงานจำนวนจริงท้ายไฟล์ ไม่ใช้เอกสารเก่าที่ระบุ 867 เป็นผลล่าสุด

39 หัวข้อ Semantic questions and answers ที่ผู้จัด dataset เพิ่มถูกกันออกจากคำตอบ/embedding ไว้แล้ว มีคำถาม 113 รายการเป็น query guidance เท่านั้น ไม่ใช้คำตอบที่แต่งเพิ่มเป็นหลักฐาน

## วิธีตรวจและ rebuild

```bash
./venv/bin/python -m unittest discover -s tests
./venv/bin/python scripts/audit_math_repair.py
./venv/bin/python scripts/audit_english_search.py
```

การสแกนข้อความใหม่โดยเก็บไฟล์รูปเดิม:

```bash
./venv/bin/python scripts/rescan.py --language=en --text-only
```

สำรอง metadata/vector_store ก่อนทุกครั้ง การสแกนเต็มที่ไม่ใส่ --text-only จะเขียนภาพตาม figure_specs อีกครั้ง ให้ทำเมื่อจำเป็นจริง ๆ หลัง rebuild ต้องตรวจ vector fingerprint และสร้างใหม่หากจะเปิด vector retrieval ห้ามนำ vector เก่าที่ text/IDs ไม่ตรงกลับมาใช้

ไฟล์ glyph map ใช้ได้กับ source PDF hash ที่กำหนดเท่านั้น หากเปลี่ยน PDF/font ระบบจะไม่ใช้ mapping เดิมโดยอัตโนมัติ ต้องตรวจ glyph ใหม่ ไม่ควรลบ guard เพื่อบังคับใช้ mapping

## Embeddings และข้อจำกัดที่ต้องทราบ

สถานะปัจจุบันคือ 0/868 embeddings โมเดล `gemini-embedding-001` ขนาด 768 ก่อนหน้านี้ API ตอบ quota 429 จึงยังไม่มี rebuilt-vector benchmark การค้น exact heading/keyword และ LLM selection ยังใช้ได้ตามเงื่อนไข key/provider แต่ไม่ควรรายงานว่าระบบนี้ทดสอบ vector retrieval ครบแล้ว `scripts/build_vectors.py --help` อธิบาย options ก่อนสร้าง ใช้ `RETRIEVAL_DOCUMENT` สำหรับเอกสารและ `RETRIEVAL_QUERY` สำหรับคำถาม โมเดลและมิติต้องตรงกัน ตรวจ `status.json` หลังสร้างเสร็จ

จำนวนข้อความที่ตรงตัวตรวจสัญลักษณ์เสียเหลือ 0 ไม่ได้หมายความว่าสูตรทั้งหมดถูกต้องแล้ว เศษส่วน, summation limits และโครงสร้างสองมิติยังอาจมี reading order ไม่ตรงภาพ PDF การกู้ glyph ไม่ใช่ OCR สมบูรณ์ ให้ตรวจ Source Text และภาพ highlight ร่วมกัน สูตรที่ยังระบุ script ไม่ได้จะไม่ถูกเดา ผู้รับควรทำรายการสูตรสองมิติและ human verification ก่อนใช้เป็นผลประเมินความแม่นยำทางคณิตศาสตร์

การทดสอบ citation ตรวจตำแหน่งกับข้อความ/เอกสารจริง ไม่ใช่การวัดความเกี่ยวข้องเชิงความหมายหรือความถูกต้องการแปลทุกประโยค ทุกคำตอบเนื้อหาวิชาการต้องมีหลักฐานอังกฤษ ห้ามแก้ด้วยการให้โมเดลเติมนิยามจากความรู้ทั่วไป การทักทายเป็นบทสนทนาระบบและไม่ใช่หลักฐานจากหนังสือ

## Checklist รับงานและพัฒนาต่อ

1. ตรวจ SHA-256 ของ ZIP ตามไฟล์ข้าง ZIP แล้วตรวจ manifest หลังแตกไฟล์
2. สร้าง venv ใหม่ ใส่ key ของผู้รับ เปิดหน้าเว็บ และลองทักทาย/ถามนิยามทั้งห้า algorithms
3. ทดสอบ Efficiency, Performance, ประสิทธิภาพ ต้องครอบคลุมหน้า 7–8 และทดสอบหัวข้อ S6.7 ต้องไม่มีหน้า 89 ของ Merge sort ปน
4. เปิด PDF highlight และเทียบข้อความต้นฉบับในแผงหลักฐาน ตรวจพิกัดจริง รวมถึงกรณีหลายบรรทัดต่อกันและข้ามหน้า
5. ทดสอบ typo `selecion sort`, คำถามทีละขั้น, โค้ด, และคำถามนอก corpus โดยไม่เพิ่มข้อเท็จจริง
6. ตรวจสูตรแบบสองมิติจากภาพต้นฉบับและประเมินคำแปลกับคนอ่านไทยก่อนสรุปคุณภาพ
7. หากต้องใช้ embeddings ให้สร้างใหม่เมื่อ quota พร้อม แล้ววัด retrieval เพิ่ม แยกผล offline/LLM/vector ให้ชัดเจน
8. ก่อน push ตรวจ `.gitignore` และ secret scan อีกครั้ง ประวัติเดิมที่มี key ไม่ควรถูกเผยแพร่ ผู้ถือ key ควรเปลี่ยน key ที่เคยอยู่ในประวัติ

งานวิจัยและข้อจำกัดของการจัดข้อความ/grounding อยู่ใน docs เดิม ให้ใช้แหล่งอ้างอิงที่ตรวจแล้วและแยกสิ่งที่วิจัยรองรับออกจากผลวัดของโครงการ ไม่ควรอ้างว่า research รับรองการแปลโดยไม่มีข้อความเพิ่ม/หายแบบสมบูรณ์

## เพิ่มเติมจากการตรวจหน้าจอจริงรอบสุดท้าย

คำถามสั้น “bubble sort คือ” เดิมไม่เข้าเงื่อนไขคำนิยามเพราะรองรับเฉพาะ “คืออะไร” ทำให้เลือกชื่อหัวข้อหลายอันมาแทนเนื้อหา แก้การรับรูปคำถามนี้ร่วมกันทุก algorithm และกัน candidate ที่เป็นหัวข้อหนึ่งบรรทัดออก เพิ่มการทดสอบทั้งห้า algorithm ไฟล์ที่แก้เพิ่มคือ services/search.py, services/evidence_selection.py, services/answering.py และ tests/test_query_recovery.py ข้อความตอบเดิมใน session ไม่ได้ถูกคำนวณย้อนหลัง ต้องส่งคำถามใหม่เพื่อตรวจผลล่าสุด

การทดสอบ browser ของ S6.7 ยืนยันว่าเนื้อหาต่อเนื่องอยู่หน้า 100 แต่พบคำแปลไทยบางช่วงปนภาษาต่างประเทศและคำศัพท์ยังไม่ลื่นไหล เช่น invariant/asymptotic นี่เป็นข้อจำกัดที่ยังเหลือ ไม่ได้แก้ระบบแปลในงานซ่อม math รอบนี้ ควรตรวจและปรับ validation การแปลในงานถัดไปก่อนนำเสนอคุณภาพภาษาไทย ระบบยังอาจคงอังกฤษเมื่อการตรวจแปลไม่ผ่าน

สำหรับคำถามนิยาม ระบบยังให้ LLM เลือกเนื้อหา แต่เพิ่มย่อหน้าคำนิยามที่ตรวจพบจาก source ไว้ก่อนกลไกเสมอ เพื่อไม่ให้เลือกมาเฉพาะวิธีทำงานโดยไม่มีนิยาม ไม่สร้างคำตอบใหม่และยังตรวจ source offsets ทุกช่วง

## ตรวจทุกอัลกอริทึมและ Parenting เพิ่มเติม

`docs/ALGORITHM_QUESTIONS_PARENTING_RESULTS.json` ตรวจคำถามแนวทางทั้งหมด 113 ข้อ (Bubble 21, Selection 23, Insertion 12, Merge 19, Counting 18 และ Principles 20) พร้อม target section ของแต่ละคำถาม คำถามเหล่านี้ใช้เป็นเส้นทางค้นเท่านั้น ไม่ใช่แหล่งคำตอบที่แต่งเพิ่ม

พบและแก้ช่องว่างระหว่าง routing กับ candidate selection: เดิม 22 คำถามมี target section ถูกต้องใน index แต่ target ไม่เข้าชุดตัวเลือกให้โมเดล ตอนนี้ให้เนื้อหาภายใต้ target ที่ตรงคำถามแนวทางเข้าก่อน ranking ทั่วไป ยังคงจำกัด 48 candidates/18,000 source characters และไม่ข้าม source validation ไม่ใช้ topic ที่คาดจากคำเดียวมาตัด target ที่กำหนดไว้ เช่น “Is this insertion sort?” เป็นคำถามในส่วน stable selection variant ไม่ใช่คำสั่งให้ค้นเฉพาะ Insertion

Parenting ตรวจหัวข้อที่มีเนื้อหาครบ 306 nodes ด้วยการเทียบรายการ chunk ลูกและลำดับกับ hierarchy รวมทั้งตรวจ offsets ทุก chunk กรณี `The CLRS direction` ได้ย่อหน้าหน้า 36 ครบตั้งแต่ทิศทาง CLRS จนถึงคำเตือนเรื่อง one pass รวมข้อความที่ผู้ใช้ระบุ ไม่ตัดไว้เพียงหัวข้อหรือประโยคแรก

`docs/ALGORITHM_LIVE_SELECTION_RESULTS.json` เป็นผลเรียก Gemini จริง 10 คำถาม (คือ / ทำงานอย่างไร ของทั้งห้า algorithms) รอบล่าสุดได้คำตอบ 10/10, source offsets ตรง 10/10 และไม่มีคำตอบที่เป็นชื่อหัวข้ออย่างเดียว ผลนี้วัดเส้นทางเลือกหลักฐาน ไม่ใช่การประเมินคำแปลหรือการทดลองกับผู้ใช้ทั้งหมด

ระหว่างตรวจพบว่าโมเดลบางครั้งส่งเลขบรรทัดเป็นจำนวนเต็มแทน ID เต็ม แก้ให้รับเฉพาะเลขที่แปลงกลับเป็น line ID ที่มีอยู่จริงภายใน chunk และหน้าเดียวกันเท่านั้น เลขนอก chunk, ID ที่แต่งขึ้น, ช่วงกลับด้าน และโค้ดไม่ครบยังถูกปฏิเสธ พร้อมกำชับรูปแบบ ID ใน prompt ไม่ใช้การเดาข้อความ

คำถาม “ทำงานอย่างไร/ทำงานยังไง” ที่ลงท้ายแบบทั่วไปเข้าชุดคำอธิบายพื้นฐานร่วมกับ “คือ” เพื่อเน้น intro prose และกลไกก่อน code/proof คำถามเฉพาะเรื่องโค้ด ความซับซ้อน หรือเสถียรภาพยังใช้เส้นทางของคำถามนั้น

ทำซ้ำการตรวจเพิ่มเติม:

```bash
./venv/bin/python scripts/audit_algorithm_questions.py
```

คำถามแนวทางทั้งหมดตรวจ offline ส่วน live API ตรวจตัวอย่าง 10 ข้อเท่านั้น ไม่ได้เรียก API ครบ 113 คำถาม และไม่ควรอ้างว่าได้ semantic accuracy 100% ทั้ง corpus

## แก้การแบ่งหน้าคำตอบที่มีแต่หัวข้อ

กรณี S2.2 และ S6.7 ค้นเนื้อหาถูก แต่ตัวแบ่งหน้าวาง heading แยกจาก source set ที่มีเนื้อหาหลาย chunks ทำให้ส่วนแรกมีแต่ชื่อหัวข้อ แก้เฉพาะ ui/evidence_groups.py ให้ heading อยู่หน้าจอเดียวกับเนื้อหาที่ตามมาเสมอ แม้จำนวน units จะเกินเป้าหมาย 4 ในกรณีนั้น ไม่แยก source set ไม่เปลี่ยนข้อความและไม่รวมพิกัด highlight ข้ามช่องว่าง มี regression ใน tests/test_evidence_groups.py และ audit หัวข้อทั้งหมดว่ามีหน้าที่แสดงเฉพาะ heading หรือไม่

## สถานะล่าสุดหลังผู้ใช้สั่งให้ทำต่อในโครงการ (ยังไม่ ZIP)

`docs/HEADING_PAGE_EVIDENCE_FIX_TH.md` บันทึกผลรอบก่อนที่มี 857 chunks จึงใช้เป็นประวัติการแก้ heading และหลักฐานเท่านั้น สถานะ Runtime ปัจจุบันคือ 868 chunks ตาม `metadata/dataset.json` ZIP ที่สร้างก่อนการแก้ล่าสุดไม่ควรใช้เป็นชุดส่งมอบปัจจุบัน

## ปัจจุบัน: ลบ Q&A จาก PDF จริงแล้ว

ดู `docs/PDF_QA_REMOVAL_TH.md` และ `docs/PDF_QA_REMOVAL_RESULTS.json` ตอนนี้ PDF Runtime ไม่มี Semantic questions and answers ทั้ง 39 จุดแล้ว จำนวนหน้ายังคง 100 และตำแหน่งข้อความ/รูปอื่นไม่เปลี่ยน Q&A 113 คู่เก็บนอก Runtime ส่วนคำถามอย่างเดียวอยู่ใน reviewed_query_routes.json เพื่อช่วยค้น ชุดข้อมูลล่าสุดมี 868 chunks (คืนป้ายข้อความในรูป 11 chunks ที่เคยถูก filter เดิมกันรวมไปด้วย) คำกล่าวในบันทึกรอบก่อนว่า PDF ต้นฉบับยังไม่ถูกแก้เป็นประวัติก่อนคำสั่งลบ Q&A นี้ ยังไม่อัปเดต ZIP

## แก้การตัดกลางย่อหน้า

ดู `docs/PARAGRAPH_COMPLETION_FIX_TH.md` กรณี bubble sort ขาดท้ายหน้า 36 เกิดจากยอมรับ line range ที่จบกลางประโยคและ context_spans ของ fallback ไม่ใช่ context window เต็ม ตอนนี้ prose selections เติมครบเฉพาะ source paragraph_id รวมส่วนต่อข้ามหน้า ตรวจครบ 8 กรณีจริงใน dataset และการเรียก Gemini จริงคืนท้ายย่อหน้าที่ขาดแล้ว PDF/metadata ไม่เปลี่ยนในรอบนี้

## อัปเดต 2026-10-13: ค่าเริ่มต้นภาษาและการแปล

ค่าเริ่มต้น `แปลคำตอบเป็นภาษาไทย` ปิดไว้ จึงเริ่มอ่านจากต้นฉบับอังกฤษ และผู้ใช้เปิดเองได้เมื่อต้องการอ่านไทย ไม่มีปุ่ม `AI ช่วยเลือกหลักฐาน` ให้ผู้ใช้จัดการ: เมื่อมี API key ระบบจะเรียก AI เลือกหลักฐานให้อัตโนมัติในเบื้องหลัง หากเรียกบริการไม่สำเร็จ ระบบใช้คำอธิบายพื้นฐานจากต้นฉบับเมื่อพบคำนิยามที่ตรง แต่ถ้าไม่มีจะรายงานว่ายังเลือกหลักฐานไม่ได้และให้ลองใหม่ การมี API key หมายถึงระบบจะลองเชื่อมต่อเมื่อมีคำถาม ไม่ได้รับรองว่าเครือข่ายหรือบริการพร้อมทุกครั้ง

หน้าคำตอบไม่มีแผง `Source Text · ต้นฉบับภาษาอังกฤษ` แยกต่างหากในทุกโหมด หลักฐานที่รวมแล้วไม่เกินประมาณ 4,000 ตัวอักษรแสดงต่อเนื่องในคำตอบเดียว หากยาวกว่านั้นจึงแบ่งตามขอบเขตหลักฐานเท่าที่จำเป็น โดยไม่ตัดเนื้อหาทิ้ง ปุ่ม `ดูหลักฐาน · หน้า … · บรรทัด …` เปิด PDF พร้อมไฮไลต์ และในแผง PDF ยังเทียบข้อความต้นฉบับได้

การตรวจแปลยืนยันเฉพาะโครงสร้าง source IDs และโทเคน/ตัวเลข/สูตรที่ป้องกันไว้ ไม่ได้พิสูจน์ความหมายครบทุกประโยค การทดลองป้อนคำแปลที่ละประโยคอธิบายหนึ่งประโยคยังผ่านตัวตรวจ จึงยังไม่มีหลักประกันว่าคำแปลไทยไม่ตกหล่น ถ้าแปลไม่ได้หรือไม่ผ่านการตรวจบางอย่าง ระบบจะคงข้อความอังกฤษเดิมไว้ แต่คำแปลที่ผ่านการตรวจโทเคนก็ยังอาจมีความหมายตกหล่น ควรตรวจโดยมนุษย์ก่อนใช้อ้างอิงอย่างเป็นทางการ

ตรวจ regression เฉพาะหน้าจอ/เส้นทางเลือกหลักฐานอัตโนมัติและตัวแปลรอบนี้ผ่าน 25 tests; เป็นการตรวจโค้ดและผลจำลอง ไม่ได้ยืนยันการเชื่อมต่อ Gemini จริงในเครื่องผู้ใช้
