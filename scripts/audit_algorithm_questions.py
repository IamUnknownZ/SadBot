"""Audit all corpus routing questions and complete hierarchy retrieval, offline."""
import sys,json,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from services.ingest import load_dataset
from services.retrieval import retrieve
from services.answering import answer
from services.evidence_selection import candidate_pool
from ui.evidence_groups import group_evidence,paginate_groups

def main():
 d=load_dataset(ROOT);nodes={n['id']:n for n in d['nodes']};results=[]
 for g in d['query_guidance']:
  target=nodes[g['target_section_id']];expected=set(target['chunk_ids']);rows=retrieve(g['query'],d)
  pool=candidate_pool(g['query'],d)
  results.append(dict(question=g['query'],topic=next((c['topic'] for c in d['chunks'] if c['id'] in expected),None),
   target=target['title'],source_page=g['source_page'],target_section_id=target['id'],
   expected_chunks=len(expected),retrieval_covers_target=expected.issubset({c['id'] for c in rows}),
   candidate_has_target=bool(expected&{c['id'] for c in pool})))
 parent=[]
 for n in d['nodes']:
  if n['kind'] not in ['chapter','section','subsection'] or not n['chunk_ids']:continue
  rows=retrieve(n['title'],d,section_id=n['id']);expected=[c['id'] for c in d['chunks'] if c['id'] in set(n['chunk_ids'])]
  display_pages=paginate_groups(group_evidence(rows,d))
  def heading_only(member):return member['kind']=='heading' or (member.get('contains_heading') and len(member['line_ids'])==1)
  has_body=any(not heading_only(c) for c in rows)
  orphan=has_body and any(all(heading_only(m) for g in page for m in g['members']) for page in display_pages)
  parent.append(dict(no_heading_only_display_pages=not orphan,id=n['id'],title=n['title'],kind=n['kind'],expected=len(expected),
   complete_and_ordered=[c['id'] for c in rows]==expected,
   citations_exact=all(c['text']==d['pages'][c['page']-1]['text'][c['char_start']:c['char_end']] for c in rows)))
 probes=[]
 for topic in ['bubble','selection','insertion','merge','counting']:
  for suffix in ['',' คือ',' คืออะไร',' คือ อะไร',' ทีละขั้น']:
   q=topic+' sort'+suffix;r=answer(q,d,ROOT)
   probes.append(dict(question=q,status=r['status'],method=r.get('retrieval_method'),pages=sorted({c['page'] for c in r['evidence']}),
    topic_matches=bool(r['evidence']) and all(c['topic']==topic for c in r['evidence']),
    only_headings=bool(r['evidence']) and all(c.get('contains_heading') and len(c['line_ids'])==1 for c in r['evidence'])))
 sample=answer('The CLRS direction',d,ROOT,select_generate=lambda _:(_ for _ in ()).throw(AssertionError('exact heading called selector')))
 expected='moves left through neighboring positions. After the pass for outer index i, A[i] contains a\nsmallest remaining key, and the finalized prefix grows by one.\nMany presentations scan left to right instead. That version moves a largest remaining key\ntoward the right end and grows a finalized suffix. Both are bubble sort, but their intermediate\narrays and invariants differ. A trace question must specify the scan direction and what counts as\none pass.'
 report=dict(scope='All 113 dataset guidance questions, all nonempty hierarchy headings, and 25 basic algorithm probes. Offline; not an LLM translation or human relevance benchmark.',
  summary=dict(questions=len(results),by_topic=dict(collections.Counter(r['topic'] for r in results)),
   routed_target_complete=sum(r['retrieval_covers_target'] for r in results),candidate_target_present=sum(r['candidate_has_target'] for r in results),
   parent_nodes=len(parent),parent_complete_ordered=sum(r['complete_and_ordered'] for r in parent),citation_valid=sum(r['citations_exact'] for r in parent),parent_without_orphan_heading_pages=sum(r['no_heading_only_display_pages'] for r in parent),
   basic_probes=len(probes),basic_answered=sum(r['status']=='answered' and r['topic_matches'] and not r['only_headings'] for r in probes)),
  questions=results,parents=parent,basic_probes=probes,clrs_direction=dict(text=sample['answer'],expected_passage_exact=expected in sample['answer'],pages=sorted({c['page'] for c in sample['evidence']}),method=sample['retrieval_method']))
 (ROOT/'docs/ALGORITHM_QUESTIONS_PARENTING_RESULTS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report['summary'],ensure_ascii=False,indent=2));print('CLRS direction exact:',report['clrs_direction']['expected_passage_exact'])
if __name__=='__main__':main()
