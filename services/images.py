"""Strictly linked and reviewed dataset image selection."""
from .retrieval import plan_query,compact,cosine,features


def select_image(query,evidence,data):
    plan=plan_query(query);ids={c['id'] for c in evidence};topics={c['topic'] for c in evidence}
    wanted='exact_answer' if plan['intent']=='fact' else 'visual_explanation'
    candidates=[]
    for im in data['images']:
        if (im.get('kind') not in ('figure','diagram','flowchart','chart','table_image') or im.get('verified') is not True or im.get('curriculum_status','primary')!='primary'
            or im.get('source_sha256')!=data['document']['sha256'] or im['topic'] not in topics
            or not ids.intersection(im['linked_chunk_ids'])):
            continue
        if plan['topics'] and im['topic'] not in plan['topics']:continue
        score=1*(im['image_type']==wanted)+2*(plan['intent'] in im.get('question_intents',[]))
        score+=max((c.get('score',0) for c in evidence if c['id'] in im['linked_chunk_ids']),default=0)
        score+=cosine(features(query),features(im.get('description','')+' '+im.get('title','')))
        candidates.append((score,im))
    candidates.sort(key=lambda row:-row[0])
    return candidates[0][1] if candidates else None
