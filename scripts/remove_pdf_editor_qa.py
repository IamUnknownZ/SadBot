"""Remove complete editor Q&A text blocks without reflowing any PDF page."""
from pathlib import Path
from collections import Counter
import json,math
import pymupdf
from PIL import Image,ImageChops,ImageDraw

def qa_blocks(page):
    result=[]
    for block in page.get_text('dict',sort=True)['blocks']:
        if block['type']!=0:continue
        lines=[''.join(s['text'] for s in l['spans']) for l in block['lines']]
        if not any(t.strip()=='Semantic questions and answers' for t in lines):continue
        if lines[0].strip()!='Semantic questions and answers' or not ' '.join(lines[1:]).startswith('Q:'):
            raise ValueError('Ambiguous Q&A block; manual review required')
        result.append(dict(page=page.number+1,bbox=list(block['bbox']),text='\n'.join(lines)))
    return result

def redact_qa(source,output):
    source,output=Path(source),Path(output)
    if source.resolve()==output.resolve():raise ValueError('Write a verified candidate before replacing the source')
    plan=[]
    with pymupdf.open(source) as pdf:
        for page in pdf:
            blocks=qa_blocks(page);plan.extend(blocks)
            for block in blocks:page.add_redact_annot(pymupdf.Rect(block['bbox']),fill=(1,1,1),cross_out=False)
            if blocks:page.apply_redactions(images=0,graphics=0,text=0)
        if not plan:raise ValueError('No Q&A blocks found')
        pdf.save(output,garbage=4,deflate=True)
    return plan

def verify_edit(source,output,plan,proof_dir=None):
    by_page={}
    for block in plan:by_page.setdefault(block['page'],[]).append(pymupdf.Rect(block['bbox']))
    changed_pixels=0;max_delta=0.;words_checked=0;proof=[]
    with pymupdf.open(source) as before,pymupdf.open(output) as after:
        page_count=len(before)
        if len(before)!=len(after) or before.get_toc()!=after.get_toc():raise AssertionError('Page count or bookmarks changed')
        for a,b in zip(before,after):
            if any(list(getattr(a,k))!=list(getattr(b,k)) for k in ['rect','mediabox','cropbox']) or a.rotation!=b.rotation:
                raise AssertionError('Page geometry changed')
            rectangles=by_page.get(a.number+1,[])
            retained=[w for w in a.get_text('words',sort=True) if not any(r.contains(pymupdf.Point((w[0]+w[2])/2,(w[1]+w[3])/2)) for r in rectangles)]
            actual=b.get_text('words',sort=True)
            if [w[4] for w in retained]!=[w[4] for w in actual]:raise AssertionError(f'Other text changed on page {a.number+1}')
            for old,new in zip(retained,actual):max_delta=max(max_delta,max(abs(old[i]-new[i]) for i in range(4)))
            words_checked+=len(retained)
            if 'Semantic questions and answers' in b.get_text():raise AssertionError('Q&A heading remains')
            pa=a.get_pixmap(alpha=False);pb=b.get_pixmap(alpha=False)
            aa=Image.frombytes('RGB',(pa.width,pa.height),pa.samples)
            bb=Image.frombytes('RGB',(pb.width,pb.height),pb.samples)
            diff=ImageChops.difference(aa,bb);draw=ImageDraw.Draw(diff)
            for r in rectangles:draw.rectangle((math.floor(r.x0)-3,math.floor(r.y0)-3,math.ceil(r.x1)+3,math.ceil(r.y1)+3),fill=(0,0,0))
            if diff.getbbox():raise AssertionError(f'Pixels changed outside Q&A on page {a.number+1}')
            if rectangles:proof.append((a.number+1,aa,bb))
        if max_delta>.01:raise AssertionError('Retained text moved')
    if proof_dir:
        proof_dir=Path(proof_dir);proof_dir.mkdir(parents=True,exist_ok=True)
        for start in range(0,len(proof),10):
            sheet=Image.new('RGB',(880,1450),'#e5e5e5');draw=ImageDraw.Draw(sheet)
            for j,(page,aa,bb) in enumerate(proof[start:start+10]):
                x=(j%2)*440;y=(j//2)*290
                draw.text((x+8,y+2),f'Page {page}: before / after',fill='black')
                for k,img in enumerate([aa,bb]):
                    img=img.copy();img.thumbnail((210,267));sheet.paste(img,(x+8+k*218,y+20))
            sheet.save(proof_dir/f'qa-removal-contact-{start//10+1}.png')
        for page,aa,bb in proof:
            if page==39:
                aa.save(proof_dir/'page-39-before.png');bb.save(proof_dir/'page-39-after.png')
    return dict(pages_verified=page_count,
                removed_blocks=len(plan),affected_pages=len(by_page),retained_words_checked=words_checked,
                maximum_retained_word_coordinate_delta_points=max_delta,outside_removal_pixels_changed=changed_pixels,
                geometry_and_bookmarks_unchanged=True)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True);parser.add_argument('--output',required=True);parser.add_argument('--proof-dir',required=True)
    args=parser.parse_args();plan=redact_qa(args.source,args.output);report=verify_edit(args.source,args.output,plan,args.proof_dir)
    Path(args.proof_dir,'removal-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
