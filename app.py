"""Sorty — English-source, source-bound desktop reading companion."""
import hashlib
import json
import os
from pathlib import Path
import streamlit as st
from dotenv import dotenv_values
from services.ingest import load_dataset,safe_path
from services.answering import answer_question
from services.formatting import reading_blocks
from services.retrieval import plan_query
from services.conversation import smalltalk,generation_provider,resolve_query
from services.vectors import fingerprint,provider,search_index,MODEL,DIMENSIONS
from ui.document_viewer import evidence_preview,pdf_payload,show_pdf
from ui.reading_view import reading_html
from ui.evidence_groups import group_evidence,paginate_groups,page_evidence_groups

ROOT=Path(__file__).resolve().parent
LANGUAGES={'en':'English'}
TRANSLATION_BATCH_SIZE=2
MAX_DISPLAY_PART_CHARS=4000


@st.cache_data(show_spinner=False)
def read_dataset(language,metadata_stamp,source_stamp):
    return load_dataset(ROOT,language=language)


@st.cache_data(show_spinner=False)
def read_index(language,stamp,revision):
    folder='vector_store'
    index=json.loads((ROOT/folder/'text_index.json').read_text())
    return index if (index['revision']==revision and index.get('model')==MODEL and index.get('dimensions')==DIMENSIONS and index.get('document_task')=='RETRIEVAL_DOCUMENT' and index.get('query_task')=='RETRIEVAL_QUERY') else None


@st.cache_data(show_spinner=False)
def preview(revision,document,evidence):
    """Reader v3: download highlights contiguous source sets as blocks."""
    return evidence_preview(ROOT,document,evidence)


@st.cache_data(show_spinner=False)
def page_payload(revision,document,evidence,page):
    """Reader v3: contiguous block highlights in crop-aware PDF user space."""
    return pdf_payload(ROOT,{'document':document,'pages':[{}]*(evidence['page']-1)+[page]},evidence)


def configuration():
    local=dotenv_values(ROOT/'.env')
    primary_key=os.getenv('GEMINI_API_KEY') or local.get('GEMINI_API_KEY')
    fallback_key=os.getenv('GEMINI_API_KEY_FALLBACK') or local.get('GEMINI_API_KEY_FALLBACK')
    # Keep the deployed model pinned; a stale Streamlit Secret must not switch it.
    model='gemini-3.1-flash-lite'
    try:
        primary_key=st.secrets.get('GEMINI_API_KEY') or primary_key
    except (FileNotFoundError,KeyError):
        pass
    try:
        fallback_key=st.secrets.get('GEMINI_API_KEY_FALLBACK') or fallback_key
    except (FileNotFoundError,KeyError):
        pass
    # A supplied backup can also keep the app available while the primary
    # Streamlit secret is being added.  Do not call the same key twice.
    key=primary_key or fallback_key
    if fallback_key==key:
        fallback_key=None
    return key,fallback_key,model


def embedding_configuration(primary_key,fallback_key):
    """Use a separately budgeted key for vectors when one is configured."""
    local=dotenv_values(ROOT/'.env')
    embedding_key=os.getenv('GEMINI_EMBEDDING_API_KEY') or local.get('GEMINI_EMBEDDING_API_KEY')
    try:
        embedding_key=st.secrets.get('GEMINI_EMBEDDING_API_KEY') or embedding_key
    except (FileNotFoundError,KeyError):
        pass
    return embedding_key or fallback_key or primary_key


def submit(question,catalogs,language,use_ai,key,model,indexes,format_with_ai=True,section_id=None,
           fallback_key=None,embedding_key=None):
    history=st.session_state.messages
    casual=smalltalk(question)
    if casual and not section_id:
        history.append(dict(query=plan_query(question),status='conversation',answer=casual,evidence=[],image=None,steps=[],source_language='en'))
        return
    data=catalogs['en']
    # Routing returns only three JSON fields; a small output budget shortens
    # latency without restricting the PDF evidence shown to the reader.
    interpreter=generation_provider(key,model,max_output_tokens=300,fallback_key=fallback_key) if key else None
    dense_search=(lambda query:search_index(query,data,indexes['en'],embed=provider(embedding_key),
                  cache_path=ROOT/'vector_store'/'query_cache.sqlite3')) if embedding_key and indexes.get('en') else None
    # Preserve the user's wording while resolving explicit follow-ups to the
    # last answered book topic. New independent questions remain unchanged.
    lookup_question=question if section_id else resolve_query(question,history)
    result=answer_question(lookup_question,data,ROOT,history,generate=interpreter,select_generate=interpreter,
                           dense_search=dense_search,section_id=section_id)
    result['query']['original']=question;result['source_language']='en';result['steps']=[]
    # Human-reviewed translations work without an API. Gemini is only needed
    # for passages that do not have a source-locked reviewed translation.
    result['display_text']={};result['translate_enabled']=bool(format_with_ai)
    history.append(result)


def translate_visible(message,shown,key,model,fallback_key=None):
    from services.translation import translate_passages
    if not message.get('translate_enabled'):return
    missing=[e for e in shown if e['id'] not in message['display_text']]
    if missing:
        with st.spinner('กำลังแปลข้อความจากต้นฉบับ…'):
            generate=(generation_provider(key,model,max_output_tokens=1800,fallback_key=fallback_key,
                        timeout_ms=120000,transient_attempts=1) if key else None)
            for start in range(0,len(missing),TRANSLATION_BATCH_SIZE):
                batch=missing[start:start+TRANSLATION_BATCH_SIZE]
                message['display_text'].update(translate_passages(batch,generate=generate))



def retry_failed_translations(message_index,chunk_ids):
    """Let the user retry 503/invalid-model translations without a new question."""
    messages=st.session_state.get('messages',[])
    if not 0<=message_index<len(messages):return
    translations=messages[message_index].get('display_text',{})
    for chunk_id in chunk_ids:
        if not translations.get(chunk_id,{}).get('translated'):
            translations.pop(chunk_id,None)


def change_part(index,total,direction):
    name=f'part-{index}'
    st.session_state[name]=max(0,min(total-1,st.session_state.get(name,0)+direction))


def reveal(index,total,all_steps=False):
    key=f'revealed-{index}'
    st.session_state[key]=total if all_steps else min(total,st.session_state.get(key,1)+1)


def clear():
    st.session_state.messages=[]
    for key in list(st.session_state):
        if key.startswith(('revealed-','part-','choice-')) or key in ('selected_evidence','selected_evidence_language','close-evidence-popup'):
            del st.session_state[key]


def close_evidence():
    st.session_state.pop('selected_evidence',None)
    st.session_state.pop('selected_evidence_language',None)


def evidence_popup(data,evidence,revision,language):
    with st.container(horizontal=True,vertical_alignment='center',key='evidence-popup-header'):
        st.button('ปิด',key='close-evidence-popup',help='ปิดแผงหลักฐาน',on_click=close_evidence)
        st.markdown('### หลักฐานจากหนังสือ')
    numbers=[int(l.split('-l')[-1]) for l in evidence['line_ids']]
    with st.container(key='evidence-popup-meta'):
        st.caption(data['document']['title'])
        st.caption(f"หน้า PDF {evidence['page']} · บรรทัด {min(numbers)}–{max(numbers)}")
        st.caption(' › '.join(evidence.get('heading_path',[])[1:]))
    page=data['pages'][evidence['page']-1]
    payload=page_payload(revision,data['document'],evidence,page)
    show_pdf(payload,key='evidence-reader')
    with st.expander('เทียบข้อความต้นฉบับ'):st.text(evidence['text'])
    lines=[l for l in page['lines'] if l['id'] in evidence['line_ids']]
    _,pdf=preview(revision,data['document'],dict(evidence,lines=lines))
    with st.container(horizontal=True):
        st.download_button('ดาวน์โหลดหน้าพร้อมไฮไลต์',pdf,file_name=f"{language}-evidence-page-{evidence['page']}.pdf",mime='application/pdf')
        st.button('กลับไปอ่านคำตอบ',key='return-from-evidence',type='primary',on_click=close_evidence)
    st.caption('เลขบรรทัดนับจากข้อความที่สแกนในหน้านี้')


def run():
    st.set_page_config(page_title='Sorty · อ่าน เข้าใจ ตรวจสอบ',page_icon='📖',layout='wide',initial_sidebar_state='collapsed')
    st.markdown('''<style>
    .block-container{max-width:980px;padding-top:2rem;padding-bottom:5rem}
    [data-testid="stBottomBlockContainer"]{max-width:980px;margin-left:auto;margin-right:auto}
    [data-testid="stAppViewContainer"]{background:#101214}
    [data-testid="stSidebar"]{background:#171a1d;border-right:1px solid #30373b}
    [data-testid="stChatMessage"]{min-width:0;box-sizing:border-box;padding:1.15rem;background:#1a1e21;border:1px solid #30373b;border-radius:16px;box-shadow:0 4px 18px #00000012}
    [data-testid="stChatMessageContent"]{min-width:0;max-width:100%;overflow-wrap:anywhere}
    [data-testid="stChatMessageContent"] [data-testid="stVerticalBlock"]{min-width:0;max-width:100%}
    [data-testid="stChatMessageContent"] p{line-height:1.8}
    .source-reading{font-size:1.05rem;line-height:1.95;max-width:70ch}
    .source-reading p{margin:0 0 1rem;white-space:pre-wrap}
    .source-reading p:last-child{margin-bottom:.25rem}
    .source-reading code{display:inline-block;padding:.1rem .5rem;border:1px solid #3a4942;border-radius:6px;background:#222e28;color:#bce5cd;font-size:1em;white-space:nowrap}
    [data-testid="stImage"] img{max-width:100%;height:auto;object-fit:contain}
    [data-testid="stCode"]{max-width:100%;border:1px solid #364047;border-radius:10px}
    [data-testid="stCode"] pre{margin:0;padding:.75rem 1rem!important;font-size:.88rem!important;line-height:1.55!important}
    .source-reading pre{white-space:pre-wrap;font-size:.95rem;line-height:1.7}
    h1{font-size:2rem!important;line-height:1.3!important}
    [data-testid="stText"]{line-height:1.9;font-size:1rem;white-space:pre-wrap;overflow-wrap:anywhere;font-family:inherit}
    .stButton button,.stDownloadButton button{border-radius:10px;min-height:42px}
    h1,h2,h3{color:#d5eade;letter-spacing:-.025em}iframe{border-radius:10px}
    .st-key-evidence-popup{position:fixed!important;right:20px!important;top:calc(50% + 22px)!important;bottom:auto!important;transform:translateY(-50%)!important;z-index:100000!important;width:min(42vw,560px)!important;height:min(81vh,820px)!important;max-height:calc(100vh - 64px)!important;box-sizing:border-box!important;overflow-y:auto!important;padding:12px!important;background:#171b1f!important;border:1px solid #394248!important;border-radius:16px!important;box-shadow:0 16px 48px #0009!important}
    .st-key-evidence-popup [data-testid="stVerticalBlock"]{gap:.08rem!important}
    .st-key-evidence-popup [data-testid="stCustomComponentV1"],.st-key-evidence-popup iframe{width:100%!important;max-width:100%!important}
    .st-key-evidence-popup-header [data-testid="stHorizontalBlock"]{align-items:center!important}
    .st-key-evidence-popup-header [data-testid="stElementContainer"]{display:flex!important;align-items:center!important;margin:0!important;padding:0!important}
    .st-key-evidence-popup-header h3{margin:0!important;font-size:1.02rem!important;line-height:30px!important}
    .st-key-evidence-popup-meta [data-testid="stElementContainer"]{margin:0!important;padding:0!important}
    .st-key-evidence-popup-meta [data-testid="stVerticalBlock"]{gap:0!important}
    .st-key-evidence-popup-meta [data-testid="stCaptionContainer"]{line-height:1!important;margin:0!important;padding:0!important}
    .st-key-evidence-popup-meta [data-testid="stCaptionContainer"] p{font-size:.72rem!important;line-height:1!important;margin:0!important;padding:0!important}
    .st-key-evidence-popup .st-key-close-evidence-popup button{display:flex!important;align-items:center!important;justify-content:center!important;transform:translateY(5px)!important;width:52px!important;min-height:30px!important;height:30px!important;padding:0 .4rem!important;border:1px solid #c93c46!important;border-radius:8px!important;background:#b72f3a!important;color:#fff!important;font-size:.78rem!important;line-height:1!important}
    .st-key-evidence-popup .st-key-close-evidence-popup button:hover{background:#982631!important;border-color:#982631!important;color:#fff!important}
    @media(max-width:900px){.st-key-evidence-popup{right:12px!important;top:auto!important;bottom:32px!important;transform:none!important;width:calc(100vw - 24px)!important;height:min(70vh,680px)!important;max-height:calc(100vh - 64px)!important}}
    </style>''',unsafe_allow_html=True)
    catalogs={};indexes={};revisions={}
    try:
        for lang in LANGUAGES:
            path=ROOT/'metadata/dataset.json'
            header=json.loads(path.read_text())['document']
            data=read_dataset(lang,path.stat().st_mtime_ns,safe_path(ROOT,header['file']).stat().st_mtime_ns)
            catalogs[lang]=data;revisions[lang]=hashlib.sha256(path.read_bytes()).hexdigest()
            indexpath=ROOT/'vector_store/text_index.json'
            indexes[lang]=read_index(lang,indexpath.stat().st_mtime_ns,fingerprint(data)) if indexpath.exists() else None
    except (OSError,ValueError,KeyError,TypeError):
        st.error('ชุดข้อมูลยังไม่พร้อม กรุณาสแกน PDF อังกฤษตามคู่มือก่อนเปิดใช้งาน');st.stop()
    revision=':'.join(revisions.values())
    if st.session_state.get('revision')!=revision:clear();st.session_state.revision=revision
    st.session_state.setdefault('messages',[])
    key,fallback_key,model=configuration()
    embedding_key=embedding_configuration(key,fallback_key)
    with st.sidebar:
        st.title('📖 Sorty');st.caption('อ่าน เข้าใจ และตรวจสอบจากหนังสือ')
        st.divider()
        language='en'
        st.caption('ต้นฉบับภาษาอังกฤษ · 100 หน้า')
        data=catalogs['en']
        st.download_button('ดาวน์โหลด PDF ต้นฉบับอังกฤษ',safe_path(ROOT,data['document']['file']).read_bytes(),
            file_name=Path(data['document']['file']).name,mime='application/pdf',width='stretch')
        st.divider()
        use_ai=bool(key)
        # Thai is the default reading language; users may explicitly switch
        # back to original English while keeping all PDF evidence unchanged.
        format_with_ai=st.toggle('แปลคำตอบเป็นภาษาไทย',value=True)
        if not key:st.caption('ไม่มี Gemini API: แปลได้เฉพาะข้อความที่มีคำแปลในเครื่อง ส่วนอื่นยังแสดงต้นฉบับอังกฤษ')
        st.caption('คำถามพื้นฐานค้นจาก PDF ได้โดยตรง · Gemini ช่วยตีความคำถามที่ซับซ้อน')
        st.caption(f'โมเดลที่ใช้: {model}')
        st.caption('ค้นจากหัวข้อ ข้อความ และความหมายใน PDF' if indexes.get('en') else 'ค้นจากหัวข้อและข้อความใน PDF')
        st.caption('ไม่มีบัญชีผู้ใช้หรือฐานข้อมูล บทสนทนาอยู่ชั่วคราวในรอบใช้งานนี้')
        st.button('เริ่มบทสนทนาใหม่',on_click=clear,width='stretch')
    question=st.chat_input('ถามเรื่องอัลกอริทึม หรือหัวข้อในหนังสือ')
    if question:
        with st.spinner('กำลังค้นหลักฐานจากหนังสือ…'):submit(question,catalogs,language,use_ai,key,model,indexes,format_with_ai,
            fallback_key=fallback_key,embedding_key=embedding_key)
    if not st.session_state.messages:
        st.markdown('## ผม Sorty ยินดีให้บริการ')
        st.write('ความรู้เรื่องอัลกอริทึมการเรียงลำดับ')
    for i,message in enumerate(st.session_state.messages):
        with st.chat_message('user'):st.write(message['query']['original'])
        with st.chat_message('assistant',avatar='📖'):
            if message['status']=='choose_section':
                st.write(message['answer'])
                choices=message['choices']
                selected=st.selectbox('หัวข้อที่พบ',range(len(choices)),key=f'choice-{i}',
                    format_func=lambda n:' › '.join(choices[n]['heading_path'][1:])+f" · หน้า {choices[n]['page_start']}–{choices[n]['page_end']}")
                if st.button('อ่านหัวข้อนี้',key=f'read-choice-{i}'):
                    submit(message['query']['original'],catalogs,'en',use_ai,key,model,indexes,format_with_ai,
                           section_id=choices[selected]['id'],fallback_key=fallback_key,embedding_key=embedding_key);st.rerun()
                continue
            if message['status']!='answered':st.write(message['answer']);continue
            if message.get('selection_state')=='unavailable':
                st.caption('AI เลือกหลักฐานยังไม่พร้อม รอบนี้ใช้คำอธิบายพื้นฐานจากต้นฉบับ')
            evidence=message['evidence']
            parts=paginate_groups(group_evidence(evidence,catalogs['en']),max_chars=MAX_DISPLAY_PART_CHARS)
            if not parts:
                st.write('คำตอบนี้ไม่มีหลักฐานจาก PDF ให้ตรวจสอบ จึงยังแสดงเป็นคำตอบไม่ได้ครับ')
                continue
            total=len(parts)
            part_key=f'part-{i}'
            part=min(st.session_state.setdefault(part_key,0),total-1)
            st.session_state[part_key]=part
            shown_groups=page_evidence_groups(parts[part],catalogs['en'])
            shown=[e for group in shown_groups for e in group['members']]
            im=message['image']
            visible_image_ids=(set(im['linked_chunk_ids']) if im and
                               set(im['linked_chunk_ids']).intersection(e['id'] for e in shown) else set())
            translate_visible(message,shown,key,model,fallback_key=fallback_key)
            # Group a plain pairwise comparison by the two requested sorting
            # methods, without rewriting the evidence or inventing a fact.
            pair_topics=[t for t in message.get('query',{}).get('topics',[])
                         if t in ('bubble','selection','insertion','merge','counting')]
            show_pair_labels=(message.get('retrieval_method')=='common_source_question'
                              and len(pair_topics)==2)
            # A small source-grounded comparison answers the learner's question
            # directly, before the exact verifiable PDF passages appear below.
            # Only enable the authored table for a fully verified source set
            # Bubble/Merge pair; never extrapolate it to arbitrary questions.
            source_ids={e['id'] for e in evidence}
            if (show_pair_labels and set(pair_topics)=={'bubble','merge'} and
                source_ids=={'p27-c0257','p28-c0269','p34-c0344','p40-c0415','p72-c0759','p78-c0826'}):
                if message.get('translate_enabled'):
                    st.markdown('''| ประเด็น | Bubble Sort | Merge Sort |
|---|---|---|
| หลักการ | สลับสมาชิกที่อยู่ติดกันเมื่อเรียงผิดลำดับ | ใช้แนวคิด Divide and Conquer |
| เวลาที่ดีที่สุด | `Theta(n^2)` สำหรับแบบวนรอบตายตัว; `Theta(n)` สำหรับแบบหยุดเมื่อไม่มีการสลับ | `Θ(n lg n)` สำหรับ Merge Sort มาตรฐาน |
| เวลาที่แย่ที่สุด | `Theta(n^2)` | `Θ(n lg n)` |
| พื้นที่เพิ่มเติม | `O(1)` | `O(n)` สำหรับอาร์เรย์ชั่วคราว และสแตกเรียกซ้ำลึก `O(log n)` |
| ความเสถียร | เสถียรเมื่อสลับเฉพาะคู่ที่ซ้ายมากกว่าขวาอย่างเคร่งครัด | เสถียรเมื่อคีย์เท่ากันแล้วเลือกข้อมูลจากฝั่งซ้ายก่อน |
| ข้อแลกเปลี่ยนหลัก | ใช้พื้นที่เพิ่มน้อย แต่เวลาโตแบบกำลังสอง | เวลาโตแบบ `n lg n` แต่ต้องมีพื้นที่สำหรับผสานข้อมูล |''')
                else:
                    st.markdown('''| Aspect | Bubble Sort | Merge Sort |
|---|---|---|
| Method | Swap adjacent out-of-order elements | Divide and conquer |
| Best-case time | `Theta(n^2)` fixed-loop; `Theta(n)` with early exit | `Θ(n lg n)` for standard merge sort |
| Worst-case time | `Theta(n^2)` | `Θ(n lg n)` |
| Auxiliary space | `O(1)` | `O(n)` temporary array and `O(log n)` recursion depth |
| Stability | Stable with strict adjacent swaps | Stable when ties take from the left run first |
| Main tradeoff | Constant extra space, but quadratic growth | `n lg n` growth, but requires merge storage |''')
                st.caption('สรุปจากหลักฐานใน PDF หน้า 27, 28, 34, 40, 72 และ 78 · เปิดดูข้อความต้นฉบับด้านล่าง')
            last_pair_topic=None
            for group in shown_groups:
                if show_pair_labels and group.get('members'):
                    group_topic=group['members'][0].get('topic')
                    if group_topic in pair_topics and group_topic!=last_pair_topic:
                        st.markdown(f'#### {group_topic.title()} Sort')
                        last_pair_topic=group_topic
                for e in group['members']:
                    display=message.get('display_text',{}).get(e['id'],dict(text=e['text'],translated=False))
                    if e.get('kind')=='figure_label' and e['id'] in visible_image_ids:
                        # The linked source image already contains these labels; retain their evidence link without duplicating them as code-like text.
                        pass
                    elif e.get('kind')=='heading':
                        st.markdown(reading_html([display['text']]),unsafe_allow_html=True)
                    elif e.get('kind')=='code':
                        st.caption('รหัสเทียม · คงโค้ดต้นฉบับ')
                        st.code(e['text'],language=None,wrap_lines=False,width='content',height='content')
                    elif e.get('kind') in ('formula','table'):
                        st.code(e['text'],language=None,wrap_lines=True)
                    else:st.markdown(reading_html([display['text'].replace('\n',' ') if not display['translated'] else display['text']]),unsafe_allow_html=True)
                    from services.translation import UNSAFE
                    if UNSAFE.search(e['text']):st.caption('Text layer มีสัญลักษณ์คณิตศาสตร์ที่ถอดรหัสไม่ครบ กรุณาตรวจสูตรจากหน้า PDF ต้นฉบับ')
                    if message.get('translate_enabled') and not display['translated'] and e.get('kind') not in ('heading','code','figure_label'):
                        reason=display.get('reason','')
                        if reason=='translation_unavailable':
                            st.caption('แปลข้อความส่วนนี้ไม่สำเร็จในรอบนี้ จึงแสดงต้นฉบับภาษาอังกฤษ')
                        elif reason=='unsafe_pdf_text':
                            st.caption('ส่วนนี้มีอักขระจาก PDF ที่อ่านได้ไม่แน่นอน จึงยังไม่แปล กรุณาตรวจจากต้นฉบับ')
                        elif reason=='protected_source_kind':
                            st.caption('คงโค้ด ตาราง หรือสูตรในรูปแบบต้นฉบับเพื่อป้องกันความคลาดเคลื่อน')
                        elif reason=='translation_requires_provider':
                            st.caption('ยังแปลส่วนนี้ไม่ได้ เพราะไม่มีบริการแปลที่ใช้งานได้')
                        elif reason in ('protected_tokens_mismatch','numeric_tokens_mismatch','invalid_translation_ids','empty_translation','translation_not_thai'):
                            st.caption('ระบบตรวจพบว่าคำแปลอาจทำให้ตัวเลข สูตร หรือข้อความสำคัญคลาดเคลื่อน จึงแสดงต้นฉบับเพื่อความถูกต้อง')
                numbers=[int(l.split('-l')[-1]) for l in group['line_ids']]
                label=f"ดูหลักฐาน · หน้า {group['page']} · บรรทัด {min(numbers)}–{max(numbers)}"
                if st.button(label,key=f'e-{i}-{group["id"]}'):
                    st.session_state.selected_evidence=group
                    st.session_state.selected_evidence_language='en'
            # A failed translation was cached for this chat turn. Expose an
            # explicit retry after a provider outage instead of requiring the
            # learner to retype the exact same question or clear the session.
            retryable_reasons={'translation_unavailable','protected_tokens_mismatch',
                               'numeric_tokens_mismatch','invalid_translation_ids',
                               'empty_translation','translation_not_thai',
                               'translation_requires_provider'}
            retryable=[e['id'] for e in shown if message.get('display_text',{}).get(e['id'],{}).get('reason') in retryable_reasons]
            if message.get('translate_enabled') and key and retryable:
                st.button('ลองแปลข้อความที่ยังไม่สำเร็จอีกครั้ง',key=f'retry-translation-{i}-{part}',
                          on_click=retry_failed_translations,args=(i,retryable))
            if im and visible_image_ids:
                st.image(safe_path(ROOT,im['file']).read_bytes(),caption=f"{im['title']} · หน้า {im['page']}",width='stretch')
            if total>1:
                st.caption('เนื้อหายาว จึงแบ่งเป็นส่วนให้อ่านต่อได้ครบ')
                with st.container(horizontal=True):
                    if message.get('translate_enabled'):
                        previous_label,next_label='ส่วนก่อนหน้า','ส่วนถัดไป'
                    else:
                        previous_label,next_label='Previous part','Next part'
                    st.button(previous_label,key=f'prev-{i}',disabled=part==0,on_click=change_part,args=(i,total,-1))
                    st.button(next_label,key=f'next-{i}',disabled=part==total-1,on_click=change_part,args=(i,total,1))
                with st.expander('ดูหัวข้อและหน้าที่ค้นพบทั้งหมด'):
                    for path,pages in dict.fromkeys(((' › '.join(e['heading_path'][1:]),str(e['page'])) for e in evidence)):
                        st.caption(f'{path} · หน้า {pages}')
    selected=st.session_state.get('selected_evidence')
    if selected:
        lang=st.session_state.get('selected_evidence_language','en')
        with st.container(key='evidence-popup'):
            evidence_popup(catalogs[lang],selected,revisions[lang],lang)

if __name__=='__main__':run()
