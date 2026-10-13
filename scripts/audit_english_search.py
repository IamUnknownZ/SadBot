"""Reproducible offline acceptance audit, with explicit gold pages and legacy baseline."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import collections
import importlib.util
import json
import statistics
import tarfile
from services.ingest import load_dataset,extract_document
from services.retrieval import retrieve
from services.search import matched_headings
from services.answering import answer
from services.translation import UNSAFE
from services.vectors import fingerprint,MODEL,DIMENSIONS

OUT=ROOT/'tmp/english_rebuild'
GOLD=[('Efficiency',{7,8}),('Performance',{7,8}),('ประสิทธิภาพ',{7,8}),('อธิบายเรื่องประสิทธิภาพ',{7,8}),
 ('Algorithms and other technologies',{8}),('The structure of the data',{9,10}),('ISBN',{3}),('Contents',{4}),('Introduction',{9}),
 ('satellite',{9,10,26,46,92,94,97}),('Analyzing algorithms',{61,62,63,64,65,66}),
 ('Bubble Sort ทีละขั้น',{38}),('Selection Sort ขั้นตอน',{47}),('Insertion Sort ทีละขั้น',{67}),
 ('Merge Sort ทีละขั้น',{83}),('Counting Sort ขั้นตอน',{95})]


def evaluate(data,search):
    records=[]
    for query,gold in GOLD:
        rows=search(query,data);pages={r['page'] for r in rows};covered=pages&gold
        records.append(dict(query=query,expected_pages=sorted(gold),found_pages=sorted(pages),
            page_recall=len(covered)/len(gold),first_12_page_recall=len({r['page'] for r in rows[:12]}&gold)/len(gold),
            chunks=len(rows),ids=[r['id'] for r in rows]))
    return records


def main():
    OUT.mkdir(exist_ok=True);data=load_dataset(ROOT)
    new=evaluate(data,retrieve)
    old_path=OUT/'legacy_retrieval.py'
    with tarfile.open(ROOT/'OLD/english-rebuild-2026-10-13/before-rebuild.tar.gz') as archive:
        old_path.write_bytes(archive.extractfile('services/retrieval.py').read())
    spec=importlib.util.spec_from_file_location('legacy_retrieval',old_path);legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    old=json.loads((ROOT/'OLD/english-rebuild-2026-10-13/retired-runtime/metadata/en/dataset.json').read_text())
    baseline=evaluate(old,legacy.retrieve)
    counts=collections.Counter(n['kind'] for n in data['nodes'])
    headings=[n for n in data['nodes'] if n['kind'] in ('chapter','section','subsection') and n['chunk_ids']]
    found=sum(n['id'] in {hit['id'] for hit in matched_headings(n['title'],data)} for n in headings)
    coverage=[]
    for n in headings:
        got=retrieve(n['title'],data,section_id=n['id'])
        coverage.append(set(c['id'] for c in got)==set(n['chunk_ids']))
    line_ids=[l for c in data['chunks'] for l in c['line_ids']]
    expected=[l['id'] for page in data['pages'] for l in page['lines'] if l['role'] not in ('running_header','editor_qa_excluded')]
    citation_ok=0
    for c in data['chunks']:
        page=data['pages'][c['page']-1];actual=[l for l in page['lines'] if l['id'] in c['line_ids']]
        citation_ok+=bool(c['text']==page['text'][c['char_start']:c['char_end']] and len(actual)==len(c['line_ids']) and c['document_id']==data['document']['id'])
    image_ok=0
    for im in data['images']:
        linked=[c for c in data['chunks'] if c['id'] in im['linked_chunk_ids']]
        image_ok+=bool(im['verified'] and im['kind'] in ('figure','diagram','flowchart','chart','table_image') and linked and all(c['section_id']==im['linked_section_id'] and c['page']==im['source_page'] for c in linked))
    negative=['10 คูณ 10 ทำไมเท่ากับ 100','หวยคืนนี้ออกเลขอะไร','ผู้แต่ง Bubble Sort คือใคร','Bubble Sort เรียง [9,7,4] ให้หน่อย']
    negatives=[dict(query=q,status=answer(q,data,ROOT)['status']) for q in negative]
    # Experiment: repeat the same gold page checks for three line-boundary child sizes.
    experiments=[]
    specs=json.loads((ROOT/'metadata/figure_specs.json').read_text())
    for size in [900,1800,3000]:
        variant=extract_document(ROOT/data['document']['file'],ROOT,specs,max_chars=size)
        scores=evaluate(variant,retrieve)
        lengths=[len(c['text']) for c in variant['chunks']]
        experiments.append(dict(max_chars=size,overlap=0,chunks=len(lengths),mean_chars=statistics.mean(lengths),
            p95_chars=sorted(lengths)[int(.95*len(lengths))],max_actual_chars=max(lengths),
            mean_gold_page_recall=statistics.mean(r['page_recall'] for r in scores)))
    status=json.loads((ROOT/'vector_store/status.json').read_text()) if (ROOT/'vector_store/status.json').exists() else dict(state='incomplete',completed=0,expected=len(data['chunks']))
    report=dict(source=data['document'],revision=fingerprint(data),counts=dict(counts,chunks=len(data['chunks']),
        vocabulary=len(data['keyword_index']['vocabulary']),images=len(data['images']),query_guidance=len(data['query_guidance'])),
        excluded_editor_qa=data['exclusions'],new_search=new,legacy_search=baseline,
        metrics=dict(heading_recall=dict(found=found,total=len(headings)),section_coverage=dict(complete=sum(coverage),total=len(coverage)),
            mean_gold_page_recall=statistics.mean(r['page_recall'] for r in new),legacy_mean_gold_page_recall=statistics.mean(r['page_recall'] for r in baseline),
            citation_integrity=dict(valid=citation_ok,total=len(data['chunks'])),body_line_coverage=dict(indexed=len(line_ids),expected=len(expected),exact=collections.Counter(line_ids)==collections.Counter(expected)),
            image_link_integrity=dict(valid=image_ok,total=len(data['images'])),
            retrieval_relevance_and_translation_fidelity='Structural tests plus limited manual live samples, not a human benchmark or 100% semantic guarantee'),
        chunk_size_experiments=experiments,negative_search=negatives,vectors=status,
        parser_warnings=dict(chunks_with_uncertain_math_text_layer=sum(bool(UNSAFE.search(c['text'])) for c in data['chunks']),
            action='Verified font-specific glyph recovery; raw spans and PDF retained. Two-dimensional formulas still require visual source verification; no LLM formula guessing'),
        unavailable_tests=['Live rebuilt-vector Recall@k: blocked by daily Gemini embedding quota','Preface/appendix retrieval: these sections are not present in this 100-page corpus'])
    (OUT/'search-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'docs/ENGLISH_SEARCH_RESULTS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(counts=report['counts'],metrics=report['metrics'],experiments=experiments,vectors=status),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
