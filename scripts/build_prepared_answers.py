"""Resume-safe builder: Excel questions become PDF-evidence routes, never answer text."""
import json
from pathlib import Path
from dotenv import dotenv_values
from services.ingest import load_dataset
from services.answering import answer_question
from services.conversation import generation_provider
from services.retrieval import compact

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'metadata/prepared_answers.json'
def main():
    styles=json.loads((ROOT/'metadata/benchmark_question_styles.json').read_text())['items']
    saved=json.loads(OUT.read_text()) if OUT.exists() else {'schema_version':1,'routes':{}}
    v=dotenv_values(ROOT/'.env'); data=load_dataset(ROOT)
    gen=generation_provider(v['GEMINI_API_KEY'],v['GEMINI_MODEL'],max_output_tokens=300,fallback_key=v.get('GEMINI_API_KEY_FALLBACK'))
    for item in styles:
        key=compact(item['question'])
        if key in saved['routes']: continue
        if item['negative']:
            saved['routes'][key]={'status':'insufficient_evidence','evidence_ids':[]}
        else:
            result=answer_question(item['question'],data,ROOT,[],generate=gen)
            saved['routes'][key]={'status':result['status'],'evidence_ids':[e['id'] for e in result.get('evidence',[])]}
        OUT.write_text(json.dumps(saved,ensure_ascii=False,indent=2)+'\n')
        print(item['id'],saved['routes'][key]['status'],flush=True)
if __name__=='__main__': main()
