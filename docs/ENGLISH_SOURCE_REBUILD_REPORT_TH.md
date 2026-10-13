# รายงาน English-Source Search-Based Chatbot — 13 ตุลาคม 2569

## ผลลัพธ์และขอบเขต

Sorty ใช้ PDF อังกฤษฉบับเดียว รับคำถามไทย ค้นหัวข้อและคำศัพท์ในเครื่อง และใช้ LLM เดิมแปลคำถาม/ข้อความหลักฐาน โครงสร้างและการค้นแบบไม่ใช้ embeddings พร้อมใช้งาน ส่วน vectors ใหม่ยังสร้างไม่ได้เพราะโควตารายวันของผู้ให้บริการตอบ 429 จึงไม่รายงานว่าการสร้าง embeddings สำเร็จ

ต้นฉบับคือ `book_data/Cormen_Basic_Sorting_100_Pages.pdf` 100 หน้า SHA-256 `0f4ed60719cbe7df3c099edd211ddbfe6b56ec2070e2852a0364195f465bd432` ไม่ได้แก้ทับ PDF ภายในมีข้อความต้นฉบับและส่วนที่ติดป้าย Supplement ต้องแยกที่มาในการอธิบาย ไม่อ้างว่าทั้งเล่มเป็นข้อความต้นฉบับ CLRS

## Root cause

1. ระบบเดิมกำหนดคำค้นตามรายชื่อหัวข้อการเรียงลำดับ ทำให้ Efficiency/ประสิทธิภาพไม่เข้าสู่การค้น แม้มีข้อความอยู่จริง
2. การตอบผูกกับการมีภาพประกอบ และกรองข้อความตามรูปที่เลือก ทำให้หัวข้อไม่มีภาพกลายเป็นไม่มีคำตอบ
3. แบ่งข้อมูลตามหน้า ไม่มี parent-child ของหัวข้อ จึงดึงย่อหน้าที่ต่อข้ามหน้าไม่ครบ และมีการจำกัดงบข้อความจนบางย่อหน้าหาย
4. คะแนนภาพ/ตัวอย่างอัลกอริทึมทำให้คำค้นทั่วไปเอนเข้าหาตัวอย่างบางเรื่อง
5. มี Q&A ที่ผู้จัดทำเพิ่มภายหลังปะปนกับเนื้อหา หากนำไป embed หรือตอบตรงจะไม่แยกหลักฐานหนังสือกับข้อความแต่งเพิ่ม
6. PDF มี crop box ต่างจาก media box ตัวอ่านเดิมกลับแกนจากความสูงหน้าที่ครอป ทำให้ไฮไลต์เหลื่อมลง ต้องแปลงจากพิกัด PyMuPDF กลับสู่ PDF user space ด้วย inverse transformation matrix ก่อนส่งให้ PDF.js
7. Text layer สูตรบางส่วนมีอักขระถอดรหัสผิดอยู่ใน PDF เดิม ไม่ควรให้โมเดลเดาความหมายเพื่อซ่อม

## การแก้คำถามขอความหมายเพิ่มเติม

คำถาม `bubble sort คือ อะไร` เดิมไม่ผ่านการตัดคำห่อคำถามเพราะมีช่องว่าง และ BM25 ให้น้ำหนัก heading ซ้ำมากจนเลือก heading ของ Supplement ส่วน `คืออะไร` ติดกันกลับ expand ทั้ง chapter จึงผิดขอบเขตคำถาม แก้ด้วย definition intent ที่เลือกย่อหน้านิยามจริงก่อน heading expansion และตรวจคำถามไทย/อังกฤษ/คำทับศัพท์ ไม่ให้ standalone headings กลายเป็นคำตอบนิยาม เลือกหน้า 34 บรรทัด 16–17 โดยคง source offsets และพิกัด ย้าย heading path อังกฤษไป Source Text แทนแสดงซ้ำเหนือคำตอบ หลังผู้ใช้ทดสอบเพิ่มเติม เปลี่ยนคำสั้นอย่าง `bubble sort` ให้เป็นคำขอความหมายโดยปริยาย ไม่เปิดทั้งบท ส่วน `อ่าน Bubble Sort ทั้งบท` หรือชื่อหัวข้อพร้อมเลขบท ยังดึง descendants ครบเมื่อขอชัดเจน ทดสอบแยกทั้งสองเจตนา

## การสำรองและย้ายข้อมูล

- สำเนาก่อนเปลี่ยน: `OLD/english-rebuild-2026-10-13/before-rebuild.tar.gz` พร้อม `source-hashes.json`
- PDF ไทย: `OLD/english-rebuild-2026-10-13/reference-only/` ใช้ตรวจด้วยคน ไม่ถูกโหลดเพื่อค้น สร้าง embeddings หรือแปลคำตอบ
- Metadata/vectors เก่า: `OLD/english-rebuild-2026-10-13/retired-runtime/`
- รูปไทยเดิม 52 รูป: `OLD/english-rebuild-2026-10-13/image-staging/` รูปอังกฤษเดิมยังเก็บไว้ และเพิ่ม crop ของภาพจริงจากต้นฉบับ
- ไม่เปลี่ยน API key และไม่ลบต้นฉบับอังกฤษ ระบบใหม่ไม่โหลด index เก่ามาชดเชยเมื่อ vectors ใหม่ไม่พร้อม

## Dataset และภาพ

| รายการ | จำนวน |
|---|---:|
| Document | 1 |
| Chapter nodes รวม front matter | 7 |
| Section | 64 |
| Subsection | 236 |
| Paragraph nodes | 853 |
| Chunks | 867 |
| คำศัพท์อังกฤษที่ parse ได้ | 2,989 |
| รูปที่ตรวจและอนุมัติ | 48 |
| Embeddings ใหม่สำเร็จ | 0/867 |

ตรวจ text layer และ layout ทุกหน้า พร้อมดู contact sheets ครบ 100 หน้า ตรวจ crop อังกฤษเดิม 38 รูป และภาพจริงที่เพิ่ม 10 รูป แก้ขอบ crop ที่ตัดอาร์เรย์ด้านซ้าย ไม่ถือว่าการตรวจนี้เป็นการพิสูจน์ทุกตัวอักษรของหนังสือ รูปไทย 52 รูปถูกแยกออกเพราะนอกขอบเขตภาษา ไม่อ้างว่าได้ตรวจใหม่ทีละภาพทั้งหมด

ทุก chunk เก็บ document/parent/section/path/page/line IDs/offset/bbox เก็บลำดับหนังสือ แบ่งตามย่อหน้าและขอบบรรทัด ไม่ overlap และไม่ข้ามหัวข้อพี่น้อง หัวข้อสั้นรวมกับย่อหน้าแรกเมื่อเป็น parent/page เดียวกัน เพื่อไม่เสียหนึ่งคำขอ embedding ให้ heading ที่แยกเดี่ยวโดยไม่จำเป็น

รูปแบ่งชนิด เช่น diagram, chart, table_image และ figure ต้องอนุมัติ เชื่อม hash ต้นฉบับและ chunk/section ที่ถูกต้อง ไม่ใช้ภาพแคปย่อหน้าเป็นภาพประกอบ และไม่ใช้รูปเป็นเงื่อนไขในการตอบ เมื่อไม่มีภาพตรงเนื้อหาจะไม่แสดงภาพ

## Q&A ที่เพิ่มภายหลัง

พบหัวข้อ `Semantic questions and answers` **39 จุด** แยก heading และข้อความ Q&A ออก **89 chunks** จากหลักฐาน/ดัชนีคำศัพท์/ข้อมูลที่จะส่งสร้าง vectors เก็บเพียง **113 คำถาม** พร้อม section เป้าหมายใน `metadata/query_guidance.json` เพื่อช่วยชี้ทางไปข้อความจริง ไม่มีคำตอบ Q&A อยู่ในข้อมูล guidance นี้

PDF เดิมและสำเนาเก่ายังอยู่ครบ การเปิดหน้าต้นฉบับอาจยังเห็น Q&A ในบริบทของหน้า แต่ส่วนที่นำมาตอบ/ไฮไลต์ต้องเป็นข้อความหลักฐานที่ผ่านการแยกแล้ว คำถามเหล่านี้เป็นตัวอย่างที่ผู้จัดทำเพิ่ม ไม่ใช่หลักฐานว่าผู้ใช้จริงถามหรือเป็นข้อมูลมนุษย์ที่ผ่านการประเมิน

## เส้นทางค้นและการใช้ API แทน embeddings

1. ทักทายด้วยข้อความที่เตรียมไว้ ไม่เรียกโมเดล
2. ค้นชื่อ heading โดยตรงหรือคำเรียกไทยที่ตรวจแล้ว เช่น Performance/ประสิทธิภาพ → Efficiency หากชื่อซ้ำให้เลือกบริบท
3. ถามชื่อหัวข้อแล้วดึง descendants ทั้งหมดตามลำดับหนังสือ รวมย่อหน้าต่อข้ามหน้า
4. คำถามทั่วไปค้น BM25 จากทุกคำที่ parse ได้ในต้นฉบับ ไม่จำกัดรายชื่ออัลกอริทึม
5. เมื่อเปิดการค้นไทย–อังกฤษและมี key ใช้ LLM แปลคำค้นไทยที่จำเป็นเป็นอังกฤษแล้วค้นในเครื่อง โมเดลไม่ได้เขียนคำตอบจากความจำ
6. เมื่อมี index ใหม่ครบและ revision/model/task ตรงกัน จึงเพิ่ม dense scores ใน hybrid retrieval ผล dense ล้วนไม่พอจะยืนยันหลักฐาน ต้องมี lexical support ด้วย ค่า threshold ยังไม่ได้ calibrate กับ embeddings จริงชุดนี้
7. ส่งเฉพาะข้อความที่ค้นพบและเปิดอ่านให้โมเดลแปลไทย ไม่ส่งทั้งเล่มทุกคำถาม คำตอบยาวอ่านทีละ 4 source units พร้อมปุ่มไปส่วนก่อนหน้า/ถัดไป

วิธีนี้ทำงานได้โดยไม่ใช้ embedding API แต่ไม่ควรสรุปว่าถูกกว่าเสมอ: การสร้าง document embeddings เป็นค่าใช้ครั้งแรกและเมื่อข้อมูลเปลี่ยน ส่วน query embeddings ใช้ทุกคำถาม; วิธีแปลคำค้นก็มี input/output tokens ต่อคำถามเช่นกัน และการแปลหลักฐานมีต้นทุนทั้งสองแบบ ต้องเปรียบเทียบยอดโทเคนจริงและอัตราปัจจุบัน ไม่เหมารวมโควตา 429 ว่าเป็นเงินถูกเรียกเก็บ ดู [ราคา Gemini API](https://ai.google.dev/gemini-api/docs/pricing) และ [เอกสาร embeddings](https://ai.google.dev/gemini-api/docs/embeddings)

## การแปลและการรักษาหลักฐาน

ใช้โมเดลเดิม `gemini-3.5-flash-lite` ให้แปลตามต้นฉบับ ไม่เพิ่มตัวอย่าง/ข้อสรุป/ข้อเท็จจริง ป้องกันตัวเลข อาร์เรย์ และช่วงสูตรด้วย markers ตรวจลำดับ/จำนวน/IDs และตัวเลขซ้ำอีกครั้ง โค้ด ตาราง และสูตรแสดงต้นฉบับ หากผลไม่ผ่านหรือ API ไม่พร้อมใช้ข้อความอังกฤษเดิม

การแปลย่อมเปลี่ยนคำจากภาษาอังกฤษเป็นไทย จึงรับประกันจำนวนคำเดิมไม่ได้ เป้าหมายคือรักษาข้อเท็จจริงและความหมาย การตรวจตัวเลข/markers ไม่พิสูจน์ว่าความหมายไม่ขาดหรือเพิ่ม 100% ทดสอบ API จริงและตรวจเทียบตัวอย่าง Efficiency แต่ยังไม่ใช่ human benchmark ทั้งเล่ม

Source Text เก็บข้อความอังกฤษเดิม Citation แสดงชื่อเอกสาร heading path หน้า PDF จริง และบรรทัด เปิด PDF.js พร้อมพิกัดบรรทัดเมื่อกดเท่านั้น ปุ่มปิดกลับไปส่วนเดิม ใช้ PDF หน้าเดียวแทนส่งทั้งเล่ม และภาพ WebP ย่อในกรอบตามสัดส่วน

## ผลทดสอบที่ทำซ้ำได้

ผลละเอียดและรายชื่อคำถาม: `docs/ENGLISH_SEARCH_RESULTS.json` สร้างด้วย `scripts/audit_english_search.py`

| การตรวจ | ผล |
|---|---:|
| ชื่อ heading ที่มีเนื้อหา พบด้วยชื่อจริง | 306/306 |
| ดึง descendants ครบตาม parent ที่เลือก | 306/306 |
| พิกัด/ช่วงข้อความ citation ตรงต้นฉบับ | 867/867 |
| บรรทัดเนื้อหาหลังตัด running headers และ Q&A ครบครั้งเดียว | 4,435/4,435 |
| ภาพเชื่อม hash/หน้า/chunks ถูกต้อง | 48/48 |
| ค่าเฉลี่ย gold-page recall 16 คำค้น ระบบใหม่ | 1.00 |
| ค่าเดียวกันในระบบอังกฤษเก่าที่สำรองไว้ | 0.375 |

ชุดทดสอบมี Efficiency, Performance, ประสิทธิภาพ, หัวข้อเทคโนโลยีอื่น, โครงสร้างข้อมูล, ISBN, Contents, satellite, Analyzing algorithms และขั้นตอนทั้ง 5 sorts หน้า gold ตรวจจาก PDF รวม satellite ที่ปรากฏหลายหน้า Metric นี้วัดการพบหน้าที่คาดหวัง ไม่ใช่ precision หรือความถูกต้องของคำตอบภาษาไทยทุกคำถาม การ expand parent อาจเพิ่มข้อความมากกว่าที่ผู้ใช้ต้องการ จึงต้องรายงานผลอย่างจำกัด

ทดลอง max chunk 900/1800/3000 ตัวอักษร ไม่ overlap: ได้ 876/867/867 chunks ค่าเฉลี่ย page recall เท่ากัน 1.00 จึงเลือก 1800 เพื่อเก็บย่อหน้ายาวสุด 1323 ตัวอักษรโดยไม่แบ่งเพิ่ม ไม่อ้างว่าเป็นค่าที่ดีที่สุดกับทุกเอกสาร

มี unit/AppTest ครอบคลุมข้อมูลไทยถูกปฏิเสธ, heading ซ้ำ/มีเลข, ประโยคข้ามหน้า, ไม่มีภาพยังตอบ, Q&A ไม่ปะปน, ป้องกันเลข/สูตรระหว่างแปล, คำถามนอกชุดข้อมูล, pagination และ PDF dialog การแก้ crop coordinates มี regression test round trip กับหน้า 8 จริง และ JavaScript ตรวจ zoom 50/100/200% กับ crop offset

## งานวิจัยที่สอดคล้อง และสิ่งที่ไม่ได้อ้างว่าใช้

- [DocLayNet — Pfitzmann et al., 2022](https://arxiv.org/abs/2206.01062): สนับสนุนการแยกชนิด layout และพิกัดองค์ประกอบ เราใช้ font/geometry/TOC ของ PDF และตรวจภาพด้วยคน ไม่ได้ฝึกหรือรันโมเดล DocLayNet
- [PubLayNet — Zhong et al., 2019](https://arxiv.org/abs/1908.07836): แนวคิดแยก text/title/list/table/figure สอดคล้องกับการไม่ใช้แคปข้อความเป็นภาพประกอบ ไม่ใช่ผลประเมินบนข้อมูลของเรา
- [RAPTOR — Sarthi et al., 2024](https://arxiv.org/abs/2401.18059): แสดงแนวทาง retrieval แบบลำดับชั้น แต่งานนั้น embed/cluster/summarize เป็น tree ระบบนี้ใช้ heading/parent ของต้นฉบับ ไม่สร้าง summary tree และไม่เรียกตัวเองว่า implement RAPTOR
- [Late Chunking — Günther et al., 2024](https://arxiv.org/abs/2409.04701): เน้น contextual embeddings ก่อน pooling แบ่ง chunk ระบบนี้ใส่ heading path ก่อน embed และขยาย parent ตอนค้น จึงไม่ใช่ late chunking และ Gemini API ที่ใช้ไม่เปิด token pooling ให้ทำวิธีนั้นตรง ๆ
- [Lost in the Middle — Liu et al., 2024](https://aclanthology.org/2024.tacl-1.9/): พบข้อจำกัดการใช้ข้อมูลกลาง long context เป็นเหตุผลให้หลีกเลี่ยงการส่งทั้งเล่มค้นทุกครั้งและแปลเป็นช่วง ไม่ใช่หลักฐานว่าระบบเราชนะเชิงประสิทธิภาพโดยยังไม่มี benchmark
- [Gemini Embedding — Lee et al., 2025](https://arxiv.org/abs/2503.07891) และ [เอกสาร API](https://ai.google.dev/gemini-api/docs/embeddings): รองรับแนวทาง multilingual retrieval แต่ความสามารถโมเดลไม่ใช่หลักฐานว่าดัชนีของเราพร้อม ขณะนี้ยังไม่มี vectors ชุดใหม่

การจัดย่อหน้าที่ไม่เปลี่ยนข้อความใช้การประกอบ source spans ด้วยโปรแกรมได้ หากใช้ AI เสนอจุดแบ่งต้องตรวจประกอบจากข้อความต้นฉบับ วิธีแปลไทยปัจจุบันเป็นคนละเงื่อนไขกับการจัดอังกฤษโดยรักษาอักขระเดิม และไม่ควรนำงานวิจัย layout มาอ้างว่า LLM แปลไม่มี hallucination

## ไฟล์ที่แก้ในงานนี้

- `app.py`: English-only, optional query/answer translation, revision checks, pagination, source dialog, simple welcome และภาพตามหลักฐาน
- `services/structure.py`, `services/ingest.py`: hierarchy, structure-aware chunks, QA exclusion, source provenance
- `services/search.py`, `services/retrieval.py`, `services/answering.py`: heading/BM25/hybrid, complete parent expansion, no image requirement
- `services/translation.py`: literal query/passage translation and protected-token checks
- `services/images.py`: approved real image selection
- `services/vectors.py`, `scripts/build_vectors.py`: English-only fingerprint/model/task compatibility, resumable atomic index
- `scripts/rescan.py`: rebuild English metadata, reviewed crops และ query guidance
- `ui/document_viewer.py`, `ui/pdf_viewer/geometry.mjs`, `ui/pdf_viewer/index.html`: crop-aware PDF highlight coordinates
- `scripts/audit_english_search.py`, `tests/test_english_system.py`, `tests/test_translation.py`, `tests/test_english_ui.py`, `tests/test_pdf_viewer.py`, `tests/test_pdf_geometry.mjs` และปรับ tests เดิมให้ตรงเงื่อนไขภาษาอังกฤษ
- `metadata/*.json`, `assets/images/en/`: ข้อมูลและรูปที่ rebuild
- `README.md`, `docs/REDESIGN_STATUS.md`, รายงานนี้ และผลตรวจ JSON

โครงการมีไฟล์ staged/dirty จากงานก่อนอยู่แล้ว ไม่ได้ reset/stage/commit/push ในงานนี้

## ปัญหาที่ยังเหลือ

1. Embeddings 0/867 เพราะ 429 โควตารายวัน ทางเลือกค้นด้วย vectors ยังไม่ผ่าน live integration ต้องรอ quota แล้วสร้างและประเมินใหม่; ทางเลือกแปลคำค้น+keyword ใช้ได้
2. 191 chunks มีเครื่องหมาย text layer ไม่แน่นอน โดยเฉพาะสูตร เก็บเดิมและตรวจ PDF ไม่เดาแก้ ความครบถ้วนของบรรทัดไม่ได้เท่ากับความถูกต้องของ encoding
3. ยังไม่มี independent human evaluation ของความหมายการแปล ความเกี่ยวข้อง/precision ทุกคำถาม และความเหมาะสมของ threshold vectors
4. ไม่รองรับการสร้างตัวอย่างอาร์เรย์ใหม่ที่ไม่มีหลักฐาน คำถามนอกขอบเขตและคำถามที่ค้นไม่พบตอบปฏิเสธได้ การค้นไม่พบไม่ใช่ข้อพิสูจน์ว่าไม่มีในหนังสือ


## ตรวจหน้าจอจริงล่าสุด

- ถาม `bubble sort` ตรง ๆ: แสดงคำตอบไทย 1 ย่อหน้า อ้าง PDF 34 บรรทัด 16–17 ไม่แสดง 27 ส่วน ไม่ปะปนโจทย์ Merge Sort
- ถาม `bubble sort คือ อะไร`: เลือกหลักฐานนิยามเดียวกัน และตรวจกรณีคำทับศัพท์ใน regression tests
- เปิด PDF 34: ตรวจภาพจริงแล้วไฮไลต์ตรงสองบรรทัดนิยามหลังแก้ crop transform
- Efficiency: ตรวจส่วนต่อหน้า 8 จริง และเปิดหลักฐานได้
- ภาพขั้นตอน Bubble Sort บน viewport 1440×900: รูปโหลดสำเร็จ กว้าง 741.22px เท่ากับกรอบและไม่ล้นแนวนอน
- หลักฐานภาพหน้าจอ: `tmp/english_rebuild/bubble-definition-proof.png`, `tmp/english_rebuild/pdf-proof.png`

ผลตรวจโค้ดล่าสุด: Python unittest 77 tests ผ่านทั้งหมด (72.45 วินาที); JavaScript PDF geometry และ loading-task cleanup ผ่าน; compileall และ git diff --check ผ่าน เปิดบริการที่ http://127.0.0.1:8502/ และ health endpoint ตอบ ok

### ปรับความครบถ้วนของนิยามตามการใช้งานจริง

ผู้ใช้ชี้ว่าการเลือกนิยามสองประโยคสั้นเกินไป จึงปรับ definition retrieval ให้เลือกนิยามต้นฉบับหน้า 34 พร้อมย่อหน้า The basic operation และ The CLRS direction หน้า 36 รวม 3 source units โดยแยกบท Supplement ไว้ใน citation เหมือนเดิม ไม่ดึงทั้งบท ไม่ใส่โจทย์หรือ trace หากไม่ได้ขอ ข้อความ source offsets/line IDs ยังคงตรวจตรง PDF การกำหนด heading context เป็นเส้นทางไปหลักฐาน ไม่ใช่คำตอบที่เขียนเก็บเอง ตรวจ text layer อังกฤษทั้งเล่มแล้วไม่พบคำอธิบายอุปมาฟองอากาศ จึงไม่เพิ่มอุปมานอก Dataset บันทึกข้อนี้แทนผลนิยาม 1 ย่อหน้าที่ทดสอบในเวอร์ชันก่อน

## เปลี่ยนจากกฎรายกรณีสู่ LLM เลือกหลักฐานร่วมทุกหัวข้อ

ตามคำชี้แจงผู้ใช้ การเลือกที่เหมาะสมต้องใช้กับทุกเรื่อง จึงเพิ่ม `services/evidence_selection.py` และเชื่อม `app.submit`/`services.answering.answer` ให้โมเดลเดิมทำ selection สำหรับคำถามธรรมชาติ โดยคืนเฉพาะ source chunk ID และ first/last line ID ไม่คืนคำตอบใหม่ โปรแกรมประกอบข้อความจริงจาก page offsets ตรวจช่วงตรงต้นฉบับ แล้วส่งแปลไทยแยกขั้นตอน ทุก chunk ยังคง citation เดิม ส่วน Exact Heading Lookup และ explicit whole-chapter lookup ดึงลูกครบตามเดิม โดยไม่ให้ LLM ตัดส่วนออก ชื่ออัลกอริทึมเปล่า ๆ เป็น concept question ไม่ใช่คำสั่งเปิดทั้งบท

Candidate pool ใช้ body keywords ให้ความสำคัญกว่าหัวข้อที่ซ้ำ จำกัด 48 ช่วง/18,000 source characters เพิ่มข้อความต้นบทเพื่อครอบคลุมย่อหน้าที่ไม่มี keyword ตรง ขอบเขตคำถามเรื่องเดียวใช้ metadata topic ร่วม ไม่มี answer mapping ต่ออัลกอริทึมในเส้นทาง AI ตัวเลือกอาจพลาดถ้า candidate generation ไม่พบหลักฐาน จึงยังต้องประเมิน recall/precision เพิ่ม ไม่มีการอ้างว่าการใช้ LLM ทำให้ถูกต้องเสมอ

ทดสอบ API จริง 5 คำถามต่างหัวข้อ บันทึก `tmp/english_rebuild/generic-selector-live*.json` รอบแรก Bubble สั้นเกินไป Selection เลือกโจทย์และ Insertion มี comparison เกินคำถาม รอบถัดไปดีขึ้นแต่ Selection ยังมี code เกินความหมาย จึงเพิ่มข้อจำกัดเจตนาที่ candidate pool และ selector prompt หน้าจอจริงล่าสุด Selection Sort เลือกหน้า 46 บรรทัด 5–7 โดยไม่มีโค้ด รายงานความสำเร็จนี้หมายถึงเลือก source จริงและใช้เส้นทางร่วม ไม่ใช่คะแนนความถูกต้องเชิงความหมาย 100%

Full suite 86 tests ผ่าน และ targeted selector 6 tests ผ่านหลังเพิ่ม basic-definition filter ตรวจ invalid IDs/extra text/reversed ranges/partial code/empty selection/direct heading bypass และ AppTest ยืนยันคำถาม Selection Sort เข้าตัวเลือก LLM จริง โควตา embeddings ยังไม่พร้อมตามรายงานเดิม ตัวเลือกนี้ใช้ generation API โดยไม่ต้องมี embeddings และเพิ่มค่าโทเคนตาม candidate payload จึงไม่รับประกันราคาถูกกว่าทุกกรณี
