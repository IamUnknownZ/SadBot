"""Display-only source sets; original retrieved passages remain unchanged."""
import re
from services.structure import union


def adjacent(a,b):
    pa,la=map(int,re.findall(r'\d+',a['id']))
    pb,lb=map(int,re.findall(r'\d+',b['id']))
    left,right=a['bbox'],b['bbox']
    return (pa==pb and lb==la+1 and right[1]-left[3]<=18
            and right[3]>=left[1] and min(left[2],right[2])>max(left[0],right[0]))


def source_lines(evidence,data):
    ids=set(evidence['line_ids'])
    return [l for l in data['pages'][evidence['page']-1]['lines'] if l['id'] in ids]


def highlight_regions(lines):
    groups=[]
    for line in lines:
        if groups and adjacent(groups[-1][-1],line):groups[-1].append(line)
        else:groups.append([line])
    return [union(group) for group in groups]


def group_evidence(evidence,data):
    groups=[]
    for row in evidence:
        lines=source_lines(row,data)
        if not lines:raise ValueError('Missing source lines for evidence group')
        previous=groups[-1] if groups else None
        if (previous and previous['page']==row['page'] and previous.get('section_id')==row.get('section_id')
            and previous.get('document_id')==row.get('document_id')
            and adjacent(source_lines(previous,data)[-1],lines[0])):
            previous['members'].append(row)
            previous['line_ids']+=row['line_ids']
            previous['bbox']=union(source_lines(previous,data))
            previous['text']='\n\n'.join(r['text'] for r in previous['members'])
        else:groups.append(dict(row,members=[row],line_ids=list(row['line_ids'])))
    for group in groups:
        group['id']='set-'+group['line_ids'][0]+'-'+group['line_ids'][-1]
    return groups


def paginate_groups(groups,max_units=4,*,max_chars=None):
    # Keep a standalone heading and the following source set on the same
    # display page; source sets and PDF highlight boundaries stay unchanged.
    bundles=[];pending=[]
    for group in groups:
        pending.append(group)
        heading_only=all(m['kind']=='heading' or
                         (m.get('contains_heading') and len(m['line_ids'])==1)
                         for m in group['members'])
        if not heading_only:bundles.append(pending);pending=[]
    if pending:
        if bundles:bundles[-1].extend(pending)
        else:bundles.append(pending)
    limit=max_units if max_chars is None else max_chars
    pages=[];current=[];size=0
    for bundle in bundles:
        count=(sum(len(g['members']) for g in bundle) if max_chars is None
               else sum(len(m.get('text','')) for g in bundle for m in g['members']))
        if current and size+count>limit:pages.append(current);current=[];size=0
        current.extend(bundle);size+=count
    if current:pages.append(current)
    return pages


def page_evidence_groups(groups,data):
    """One source control per visible PDF page, without filling highlight gaps."""
    pages={}
    for group in groups:
        key=(group.get('document_id'),group['page'])
        if key not in pages:pages[key]=dict(group,members=[],line_ids=[])
        page=pages[key]
        page['members'].extend(group['members'])
        page['line_ids'].extend(group['line_ids'])
    for page in pages.values():
        page['line_ids']=list(dict.fromkeys(page['line_ids']))
        page['bbox']=union(source_lines(page,data))
        page['text']='\n\n'.join(m['text'] for m in page['members'])
        page['id']='page-set-'+page['line_ids'][0]+'-'+page['line_ids'][-1]
    return list(pages.values())
