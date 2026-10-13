"""Offline source-preservation and recovered-glyph audit; never calls an API."""
import sys,json,hashlib,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from services.ingest import load_dataset,validate_dataset
from services.answering import answer
from services.translation import UNSAFE

def main():
    data=load_dataset(ROOT);validate_dataset(data,ROOT)
    baseline=json.loads((ROOT/'OLD/math-text-repair-2026-10-13/before-files-sha256.json').read_text())
    unchanged=[];changed=[]
    for name,sha in baseline.items():
        p=ROOT/name
        if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==sha:unchanged.append(name)
        else:changed.append(name)
    lines=[l for page in data['pages'] for l in page['lines']]
    repaired=[l for l in lines if l['text']!=l.get('raw_text',l['text'])]
    events=[e for l in lines for span in l['spans'] for e in span.get('repairs',[])]
    def forbidden(_):raise AssertionError('Exact heading invoked AI')
    query='S6.7 Counting sort: deep questions, limits, and corpus audit'
    result=answer(query,data,ROOT,select_generate=forbidden)
    assert {e['page'] for e in result['evidence']}=={100}
    report=dict(pages=len(data['pages']),chunks=len(data['chunks']),repaired_lines=len(repaired),
        repair_events=dict(collections.Counter(e['kind'] for e in events)),
        raw_spans_retained=all('raw_text' in s for l in lines for s in l['spans']),
        unsafe_chunks=sum(bool(UNSAFE.search(c['text'])) for c in data['chunks']),
        original_pdf_and_image_files_unchanged=not any(p.startswith(('book_data/','assets/')) for p in changed),
        changed_preexisting_files=changed,
        exact_heading_test=dict(query=query,state=result['selection_state'],pages=sorted({e['page'] for e in result['evidence']})),
        limitations=['Glyph recovery is verified against custom-font atlas; it is not a full mathematical OCR benchmark.',
          'Two-dimensional fractions and summation limits retain source geometry, but their linear reading order still needs source visual verification.',
          'Unicode scripts are recovered only for supported glyphs with a nearby mathematical base; unsupported forms remain original.'])
    (ROOT/'docs/MATH_REPAIR_RESULTS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
