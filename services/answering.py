"""English source retrieval; translation is a separate, optional presentation step."""
import re
import logging
from .retrieval import retrieve,plan_query
from .search import matched_headings,definition_rows,has_numbered_heading_prefix
from .context import token_count
from .images import select_image
from .ingest import safe_path


def _broad_heading_choices(query,hits,data):
    if len(hits)!=1 or not re.match(r'^\s*(?:S?\d+(?:\.\d+)*)\s+',query,re.I):return []
    full_scope=('ทั้งบท','ทั้งหัวข้อ','ทั้งหมด','ทุกส่วน','อ่านครบ','อ่านทั้งหมด')
    if any(term in query for term in full_scope) or re.search(r'\b(?:all|everything|entire|whole|full)\b',query,re.I):return []
    parent=hits[0]
    if len(parent.get('chunk_ids',[]))<=20:return []
    by_id={node['id']:node for node in data.get('nodes',[])}
    return [by_id[ident] for ident in parent.get('child_ids',[])
            if ident in by_id and by_id[ident]['kind'] in ('chapter','section','subsection')
            and by_id[ident].get('chunk_ids')]


def answer_question(question,data,root,history,*,generate,select_generate=None,dense_search=None,section_id=None):
    """Gemini routes first; factual answers are reconstructed from the PDF only."""
    from .question_routing import interpret_question
    base=dict(query=plan_query(question),status='insufficient_evidence',
              answer='ไม่พบข้อมูลที่รองรับคำถามนี้ในหนังสือภาษาอังกฤษครับ',
              evidence=[],image=None,choices=[])
    from .prepared_answers import answer_for
    prepared=answer_for(question,data)
    if prepared:
        prepared['query']['original']=question
        return prepared
    from .known_questions import known_negative_question
    if known_negative_question(question):
        return base
    # A bare algorithm name is a request for its concise definition.  This
    # must run before exact-heading expansion: e.g. "bubble sort" is also a
    # chapter title, but opening that chapter would be needlessly long.
    from .known_topics import known_topic
    topic=known_topic(question)
    if topic:
        result=answer(topic['canonical'],data,root,section_id=topic['section_id'])
        result['query']['original']=question
        result['prepared']=True
        result['retrieval_method']='known_topic_alias'
        return result
    # Longer exact English headings retain the parent-and-child reader view.
    from .search import matched_headings,normalize,heading_name
    exact_heading=[node for node in matched_headings(question,data)
                   if normalize(question)==heading_name(node['title'])]
    if len(exact_heading)==1:
        result=answer(question,data,root,section_id=exact_heading[0]['id'])
        result['query']['original']=question
        result['prepared']=True
        result['retrieval_method']='exact_heading_parent_children'
        return result
    if not generate:
        return dict(base,status='search_unavailable',question_route_state='unavailable',
                    answer='กรุณาตั้งค่า Gemini API เพื่อให้ระบบอ่านความหมายของคำถามก่อนค้นหนังสือครับ')
    try:
        route=interpret_question(question,history,data,generate=generate,section_id=section_id)
    except (ValueError,KeyError,TypeError,AttributeError) as exc:
        provider_error=str(exc).startswith('Model unavailable')
        match=re.search(r'status (\d+)',str(exc)) if provider_error else None
        reason='provider_unavailable' if provider_error else 'invalid_question_route'
        status=int(match[1]) if match else None
        logging.getLogger(__name__).warning('Gemini question routing: reason=%s status=%s',reason,status)
        # A transient Gemini outage must not disable source-grounded lookup.
        # Try the deterministic heading/alias/BM25 path without another model
        # call. It still returns only PDF evidence and preserves all offset
        # checks. If local retrieval has no support, keep the explicit error.
        if provider_error:
            local=answer(question,data,root,select_generate=None)
            if local.get('status')=='answered':
                local['query']['original']=question
                local['question_route_state']='local_fallback'
                local['question_route_reason']=reason
                local['question_route_provider_status']=status
                return local
        return dict(base,status='search_unavailable',question_route_state='unavailable',
                    question_route_reason=reason,question_route_provider_status=status,
                    answer='Gemini ยังส่งผลการตีความคำถามที่ระบบใช้ค้นได้ไม่สำเร็จครับ กรุณาลองใหม่อีกครั้ง')
    base['question_route']=route
    if route['mode']=='out_of_scope':return base
    from .search import definition_rows
    # Short “what is …?” questions should show the definition and basic
    # mechanism, not every exercise inside an algorithm chapter Gemini named.
    is_short_definition=bool(definition_rows(question,data))
    scores=None
    if dense_search:
        try:scores=dense_search(route['search_query'])
        except ValueError:
            logging.getLogger(__name__).warning('Vector search unavailable; using source keyword retrieval')
    # Gemini has already read the raw human question and selected its source
    # section in this one request.  Retrieval only reconstructs that original
    # section; it must not ask Gemini again to choose lines from it.
    result=answer(question if is_short_definition else route['search_query'],data,root,dense_scores=scores,
                  select_generate=select_generate,
                  candidate_section_id=None if is_short_definition else route['section_id'],
                  selection_question=question)
    result['query']['original']=question
    result['question_route']=route
    if result.get('selection_state')=='unavailable':
        logging.getLogger(__name__).warning('Gemini evidence selection: reason=%s status=%s',
            result.get('selection_reason'),result.get('selection_provider_status'))
    return result


def answer(query,data,root,*,budget=2048,dense_scores=None,section_id=None,select_generate=None,selection_question=None,
           force_selection=False,candidate_section_id=None):
    source_query=query
    original_plan=plan_query(query)
    query=original_plan['normalized']
    base=dict(query=original_plan,status='insufficient_evidence',
        answer='ไม่พบข้อมูลที่รองรับคำถามนี้ในหนังสือภาษาอังกฤษครับ',evidence=[],image=None,choices=[])
    if not query.strip():return base
    if any(w in query for w in ['ผู้แต่ง','วันเกิด','ราคา','สภาพอากาศ','พยากรณ์']):
        return base
    hits=matched_headings(query,data) if not section_id and not force_selection else []
    if len(hits)>1 and not definition_rows(query,data):
        return dict(base,status='choose_section',answer='พบหัวข้อชื่อเดียวกันหลายแห่ง เลือกส่วนที่ต้องการอ่านครับ',choices=hits)
    # A compact numbered section is a precise target; avoid a child menu for
    # its figure/exercise labels. Keep the safeguard for broad parents such as
    # "1.1 Algorithms", which contains many named subsections.
    child_ids=set(hits[0].get('child_ids',[])) if len(hits)==1 else set()
    child_heading_count=sum(node['id'] in child_ids
                            and node.get('kind') in ('chapter','section','subsection')
                            and bool(node.get('chunk_ids'))
                            for node in data.get('nodes',[]))
    exact_numbered_section=(has_numbered_heading_prefix(query) and len(hits)==1
                            and hits[0].get('kind') in ('section','subsection')
                            and child_heading_count<=2)
    broad_choices=[] if exact_numbered_section else _broad_heading_choices(query,hits,data)
    if broad_choices:
        return dict(base,status='choose_section',selection_state='broad_heading',
                    answer='หัวข้อนี้มีหลายส่วน ผมแสดงหัวข้อย่อยให้เลือกก่อน เพื่อไม่รวมข้อความจำนวนมากในคำตอบเดียวครับ',
                    choices=broad_choices)
    from .search import exact_phrase_lookup
    exact=exact_phrase_lookup(source_query,data) if not section_id and not hits and not force_selection else []
    candidates=exact or None
    selection_state='exact_phrase' if exact else 'not_requested'
    if select_generate and not exact:
        from .evidence_selection import direct_lookup,candidate_pool,select_evidence
        if force_selection or not direct_lookup(query,data,section_id):
            corrected=(selection_question or source_query) if force_selection else plan_query(selection_question or query)['normalized']
            selection=select_evidence(corrected,candidate_pool(query,data,dense_scores,section_id=candidate_section_id),data,generate=select_generate)
            selection_state=selection['state']
            base['selection_reason']=selection.get('reason')
            base['selection_provider_status']=selection.get('provider_status')
            if selection_state=='selected':
                candidates=selection['evidence']
                if not candidates and not force_selection and selection.get('intent')!='out_of_scope':
                    candidates=definition_rows(query,data)
                    if candidates:selection_state='basic_fallback'
        else:selection_state='direct_lookup'
    base['selection_state']=selection_state
    if candidates is None and selection_state=='unavailable':
        candidates=definition_rows(query,data)
        if not candidates and original_plan['intent']=='comparison' and len(original_plan['topics'])>=2:
            # When the selector is temporarily unavailable, reconstruct a
            # comparison from each requested topic's source definition. This
            # keeps both sides present without generating any new facts.
            combined=[];seen=set()
            for topic in original_plan['topics']:
                for row in definition_rows(f'{topic} sort คือ',data):
                    if row['id'] not in seen:
                        seen.add(row['id']);combined.append(row)
            candidates=combined
            if candidates:
                selection_state='local_comparison_fallback'
                base['selection_state']=selection_state
        if not candidates:
            return dict(base,status='search_unavailable',answer='ตอนนี้ AI ยังเลือกหลักฐานที่ตรงคำถามไม่ได้ครับ กรุณาลองใหม่อีกครั้ง ข้อผิดพลาดนี้ไม่ได้หมายความว่าไม่มีเนื้อหาในหนังสือ')
    if candidates is None:candidates=retrieve(query,data,dense_scores=dense_scores,section_id=section_id)
    if not candidates:return base
    # A definition needs the actual source definition, even when the selector
    # chooses only a valid paragraph about mechanics. Keep source text intact.
    definitions=definition_rows(query,data) if not section_id else []
    if definitions:
        definition=definitions[0]
        candidates=[definition]+[c for c in candidates if c['id']!=definition['id']]
    # Exact heading expansion is never clipped to an LLM context budget.
    arrays=re.findall(r'\[[0-9, \-]+\]',query)
    source=''.join(c['text'] for c in candidates).replace(' ','').replace('\n','')
    if any(a.replace(' ','') not in source for a in arrays):return base
    evidence=sorted(candidates,key=lambda c:c['order'])
    for c in evidence:
        page=data['pages'][c['page']-1]
        if c['text']!=page['text'][c['char_start']:c['char_end']]:raise ValueError('Answer evidence was modified')
    im=select_image(query,evidence,data)
    # A section link alone does not make a specific worked trace suitable for
    # a definition explaining the other scan direction.
    if (im and (evidence[0]['retrieval_method']=='definition' or evidence[0].get('selection_intent')=='definition')
        and 'left to right' in ' '.join(c['text'] for c in evidence).lower()
        and 'right-to-left' in im['title'].lower()):im=None
    if im:safe_path(root,im['file'])
    text='\n\n'.join(c['text'] for c in evidence)
    return dict(base,status='answered',answer=text,evidence=evidence,image=im,
        retrieval_method=('llm_selected_with_definition' if definitions and selection_state=='selected'
                          else evidence[0]['retrieval_method']),
        budget=dict(limit=budget,used=token_count(text),unit='source tokens; paginated, not truncated'))
