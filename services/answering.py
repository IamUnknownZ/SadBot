"""English source retrieval; translation is a separate, optional presentation step."""
import re
import logging
from .retrieval import retrieve,plan_query
from .search import matched_headings,definition_rows,has_numbered_heading_prefix
from .context import token_count
from .images import select_image
from .ingest import safe_path


def is_sorting_algorithms_overview(question):
    """A narrow beginner-definition route; never hijack complexity or comparisons."""
    from .search import normalize
    q=normalize(question).strip(' ?!.,。！？')
    english=(r'(?:(?:what (?:is|are) (?:a |an |the )?|define |explain )?'
             r'sorting algorithms?)')
    thai=rf'(?:sorting algorithms?|{re.escape(normalize("อัลกอริทึมการเรียงลำดับ"))})(?:\s*(?:คืออะไร|หมายถึงอะไร|คือ))'
    return bool(re.fullmatch(english,q) or re.fullmatch(thai,q))


def _sorting_intro_evidence(question,data):
    """First source paragraphs of 1.1; never flatten descendant subsections."""
    from .search import normalize
    if not (is_sorting_algorithms_overview(question) or normalize(question)=='1.1 algorithms'):
        return []
    parent=next((n for n in data.get('nodes',[])
                 if n.get('kind')=='section' and normalize(n['title'])=='1.1 algorithms'),None)
    if not parent:return []
    rows=[c for c in data.get('chunks',[])
          if c.get('parent_id')==parent['id'] and c.get('kind')=='paragraph'
          and c.get('curriculum_status')=='primary']
    rows.sort(key=lambda c:c['order'])
    opening=rows[:5]
    # These anchors guard against silently presenting the wrong passage when
    # the source PDF or hierarchy changes. Every selected byte remains from PDF.
    if (len(opening)!=5 or not opening[0]['text'].startswith('1.1\nAlgorithms\n')
        or 'formally deﬁne the sorting problem:' not in opening[2]['text']
        or 'Input:' not in opening[3]['text'] or 'Output:' not in opening[3]['text']
        or 'instance of the sorting problem' not in opening[4]['text']):return []
    return [dict(c,score=1.,retrieval_method='source_intro',matched_heading_ids=[parent['id']])
            for c in opening]


def _answer_from_verified_chunks(question,data,root,rows,method):
    """Return only immutable, page-offset-verified English PDF text."""
    from .context import token_count
    evidence=sorted(rows,key=lambda c:c['order'])
    for c in evidence:
        page=data['pages'][c['page']-1]
        if c['text']!=page['text'][c['char_start']:c['char_end']]:
            raise ValueError('Answer evidence was modified')
    im=select_image(question,evidence,data)
    if im:safe_path(root,im['file'])
    text='\n\n'.join(c['text'] for c in evidence)
    return dict(query=plan_query(question),status='answered',answer=text,
                evidence=evidence,image=im,choices=[],retrieval_method=method,
                budget=dict(limit=2048,used=token_count(text),unit='source tokens; paginated, not truncated'))


def answer_question(question,data,root,history,*,generate,select_generate=None,dense_search=None,section_id=None):
    """Gemini routes first; factual answers are reconstructed from the PDF only."""
    from .question_routing import interpret_question
    base=dict(query=plan_query(question),status='insufficient_evidence',
              answer='ไม่พบข้อมูลที่รองรับคำถามนี้ในหนังสือภาษาอังกฤษครับ',
              evidence=[],image=None,choices=[])
    # A user-selected child overrides the broad parent question that opened
    # the menu; otherwise clicking "read this section" loops back to the menu.
    if section_id:
        result=answer(question,data,root,section_id=section_id)
        result['query']['original']=question
        if result['status']=='answered':
            result['retrieval_method']='user_selected_section'
        return result
    from .prepared_answers import answer_for
    prepared=answer_for(question,data)
    if prepared:
        prepared['query']['original']=question
        return prepared
    from .known_questions import known_negative_question
    if known_negative_question(question):
        return base
    # A beginner definition is explicitly grounded in the opening of 1.1,
    # irrespective of Gemini quota, model availability, or a later same-named
    # subsection about comparing sorting algorithms.
    if is_sorting_algorithms_overview(question):
        result=answer(question,data,root)
        result['query']['original']=question
        return result
    # An exact copied fragment is already verifiable against the source and
    # should never be paraphrased or reinterpreted by an external model.
    from .search import exact_phrase_lookup
    if not section_id and exact_phrase_lookup(question,data):
        result=answer(question,data,root)
        result['query']['original']=question
        return result
    # Explicit named-algorithm steps without a new input array are a locally
    # indexed worked trace. This avoids an unnecessary model selection which
    # can otherwise return a single stray paragraph or no trace at all.
    step_plan=plan_query(question)
    named=[topic for topic in step_plan['topics'] if topic in ('bubble','selection','insertion','merge','counting')]
    if (not section_id and step_plan['intent']=='steps' and len(named)==1
            and len(step_plan['topics'])==1 and not re.search(r'\d',question)):
        result=answer(question,data,root)
        if (result['status']=='answered' and result['evidence']
                and all(row['topic']==named[0] for row in result['evidence'])):
            result['query']['original']=question
            result['retrieval_method']='known_steps_source'
            return result
    # Broad requests such as "compare every sort" have a dedicated source
    # summary and running-time table. Opening that compact section is faster
    # and more relevant than asking the selector to combine arbitrary mentions
    # of comparison, traces and exercises from across the book.
    from .retrieval import is_broad_sort_comparison
    if is_broad_sort_comparison(question):
        from .search import heading_name
        summary=next((node for node in data.get('nodes',[])
                      if node.get('kind') in ('section','subsection')
                      and heading_name(node.get('title',''))=='sorting algorithms'
                      and node.get('chunk_ids')),None)
        if summary:
            result=answer(question,data,root,section_id=summary['id'])
            # The original overview predates the book's labeled Bubble and
            # Selection supplements. Add their compact, source-backed direct
            # comparison so "every sort" does not silently omit both topics.
            local_pair=next((chunk for chunk in data.get('chunks',[])
                             if chunk.get('kind')=='paragraph'
                             and 'fixed-loop bubble and standard selection' in chunk.get('text','').casefold()),None)
            if result.get('status')=='answered' and local_pair:
                result['evidence']=sorted([*result['evidence'],local_pair],key=lambda row:row['order'])
                result['answer']='\n\n'.join(row['text'] for row in result['evidence'])
                result['budget']['used']=token_count(result['answer'])
            result['query']['original']=question
            result['prepared']=True
            result['retrieval_method']='broad_comparison_summary'
            return result
    # A bare algorithm name is a request for its concise definition.  This
    # must run before exact-heading expansion: e.g. "bubble sort" is also a
    # chapter title, but opening that chapter would be needlessly long.
    from .known_topics import known_topic
    # A plain algorithm-definition question must not expand all 53 chunks of
    # its parent chapter when the first two source paragraphs suffice.
    from .common_questions import source_evidence
    if question.strip().casefold() in ('อัลกอริทึมคืออะไร','อัลกอริทึมหมายถึงอะไร'):
        rows=source_evidence(question,data)
        if rows:return _answer_from_verified_chunks(question,data,root,rows,'common_source_question')
    topic=known_topic(question)
    if topic:
        result=answer(topic['canonical'],data,root,section_id=topic['section_id'])
        result['query']['original']=question
        result['prepared']=True
        result['retrieval_method']='known_topic_alias'
        return result
    # Longer exact English headings retain the parent-and-child reader view.
    from .search import matched_headings,normalize,heading_name,heading_query,numbered_heading_parts
    heading_matches=matched_headings(question,data)
    # Numbered source headings are already disambiguated by
    # matched_headings(). Compare their number and title together instead of
    # comparing "1.1 Algorithms" with a number-stripped "Algorithms".
    exact_heading=(heading_matches if numbered_heading_parts(question) and len(heading_matches)==1
                   else [node for node in heading_matches
                         if heading_name(node['title']) in (normalize(question),heading_query(question))])
    if len(exact_heading)==1:
        # Keep broad-heading pagination/child-choice safeguards. Passing the
        # section_id here would force an entire large chapter into the reply.
        result=answer(question,data,root)
        result['query']['original']=question
        result['prepared']=True
        if result['status']=='answered':
            result['retrieval_method']='exact_heading_parent_children'
        return result
    # Unambiguous definition, mechanism, complexity, stability and simple
    # two-method comparisons should not depend on provider uptime or quota.
    from .common_questions import source_evidence
    rows=source_evidence(question,data)
    if rows:
        return _answer_from_verified_chunks(question,data,root,rows,'common_source_question')
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
        from .search import matched_headings,definition_rows,exact_phrase_lookup
        if provider_error and (matched_headings(question,data)
                               or definition_rows(question,data)
                               or exact_phrase_lookup(question,data)):
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
    # Broad headings are answered with source passages, not a forced
    # subsection-picker menu. The 1.1 introduction is a bounded, verified
    # five-paragraph reading; other explicit headings retain their complete
    # reader view with pagination when needed.
    intro=_sorting_intro_evidence(source_query,data) if not section_id and not force_selection else []
    from .search import exact_phrase_lookup
    exact=exact_phrase_lookup(source_query,data) if not intro and not section_id and not hits and not force_selection else []
    candidates=intro or exact or None
    selection_state='source_intro' if intro else 'exact_phrase' if exact else 'not_requested'
    if select_generate and not exact and not intro:
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
            # A lexical hit alone does not establish that it answers a natural
            # question. Fail closed when the model is unavailable rather than
            # dumping unrelated book pages under a valid-looking citation.
            # Precise copied passages and headings are still safe to retrieve.
            from .search import exact_phrase_lookup
            if matched_headings(query,data) or exact_phrase_lookup(source_query,data):
                candidates=retrieve(query,data,dense_scores=dense_scores)
                if candidates:
                    selection_state='local_retrieval_fallback'
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
