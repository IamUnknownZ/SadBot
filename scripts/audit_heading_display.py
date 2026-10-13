"""Exercise literal heading queries, duplicate choices, pagination and page citations."""
import sys,json,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from services.ingest import load_dataset
from services.answering import answer
from ui.evidence_groups import group_evidence,paginate_groups,page_evidence_groups

def main():
 d=load_dataset(ROOT);results=[]
 def heading_only(m):return m['kind']=='heading' or (m.get('contains_heading') and len(m['line_ids'])==1)
 def forbidden(_):raise AssertionError('Literal heading unexpectedly invoked model')
 for n in d['nodes']:
  if n['kind'] not in ('chapter','section','subsection') or not n['chunk_ids']:continue
  try:a=answer(n['title'],d,ROOT,select_generate=forbidden)
  except AssertionError:
   results.append(dict(title=n['title'],status='unexpected_model_call'));continue
  initial=a['status']
  if initial=='choose_section':a=answer(n['title'],d,ROOT,section_id=n['id'],select_generate=forbidden)
  es=a['evidence'];parts=paginate_groups(group_evidence(es,d)) if es else []
  orphan=any(all(heading_only(m) for g in p for m in g['members']) for p in parts)
  controls=[]
  for part in parts:
   pages=page_evidence_groups(part,d)
   controls.append(len(pages)==len({(g.get('document_id'),g['page']) for g in part}))
  expected=set(n['chunk_ids']);got={e['id'] for e in es}
  results.append(dict(title=n['title'],kind=n['kind'],initial_status=initial,status=a['status'],method=a.get('retrieval_method'),
   chunks=len(es),display_parts=len(parts),orphan_heading=orphan,complete=expected==got,extra=len(got-expected),missing=len(expected-got),
   one_control_per_visible_pdf_page=all(controls)))
 issues=[x for x in results if x.get('orphan_heading') or x['status']!='answered' or
         (x.get('method')=='exact_heading' and not x['complete']) or not x.get('one_control_per_visible_pdf_page',False)]
 report=dict(total=len(results),statuses=dict(collections.Counter(x['status'] for x in results)),
  duplicate_titles_resolved=sum(x.get('initial_status')=='choose_section' for x in results),issues=issues,results=results)
 (ROOT/'docs/HEADING_DISPLAY_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='results'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
