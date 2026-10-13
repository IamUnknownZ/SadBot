"""Source/hash-bound recovery of visually reviewed custom math-font glyphs.

Never substitute a character globally or guess an equation from language context.
Original span text and glyph positions are retained for reproducibility.
"""
import hashlib
import json
from pathlib import Path

SUPER=dict(zip('0123456789+-=()abcdefghijklmnopqrstuvwxyz',
    '⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖ?ʳˢᵗᵘᵛʷˣʸᶻ'))
SUB=dict(zip('0123456789+-=()aehijklmnoprstuvx','₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ'))


class VerifiedMathDecoder:
    def __init__(self,pdf,map_path):
        self.enabled=False;self.fonts={};self.revision=None
        if not Path(map_path).is_file() or not pdf.name or not Path(pdf.name).is_file():return
        raw=Path(map_path).read_bytes();mapping=json.loads(raw)
        if hashlib.sha256(Path(pdf.name).read_bytes()).hexdigest()!=mapping['source_sha256']:return
        actual={}
        for page in pdf:
            for font in page.get_fonts(full=True):
                name=font[3].split('+')[-1]
                if name in mapping['fonts'] and name not in actual:
                    actual[name]=hashlib.sha256(pdf.extract_font(font[0])[3]).hexdigest()
        if any(actual.get(name)!=row['sha256'] for name,row in mapping['fonts'].items()):return
        self.enabled=True;self.fonts=mapping['fonts'];self.revision=hashlib.sha256(raw).hexdigest()

    def glyph(self,font,glyph_id,original):
        if not self.enabled:return original
        return self.fonts.get(font,{}).get('glyphs',{}).get(str(glyph_id),original)

    def blocks(self,page):
        blocks=page.get_text('dict',sort=True)['blocks']
        raw_blocks=page.get_text('rawdict',sort=True)['blocks']
        lookup={}
        if self.enabled:
            for span in page.get_texttrace():
                for _,gid,origin,_ in span['chars']:
                    lookup[(span['font'],round(origin[0],3),round(origin[1],3))]=gid
        for block,raw_block in zip(blocks,raw_blocks):
            for line,raw_line in zip(block.get('lines',[]),raw_block.get('lines',[])):
                for s,rs in zip(line['spans'],raw_line['spans']):
                    s['raw_text']=s['text'];s['repairs']=[]
                    if not self.enabled:continue
                    chars=[]
                    for offset,c in enumerate(rs['chars']):
                        key=(s['font'],round(c['origin'][0],3),round(c['origin'][1],3))
                        gid=lookup.get(key);recovered=self.glyph(s['font'],gid,c['c'])
                        chars.append(recovered)
                        if recovered!=c['c']:
                            s['repairs'].append(dict(kind='glyph',offset=offset,raw=c['c'],text=recovered,
                                glyph_id=gid,font=s['font'],bbox=list(c['bbox'])))
                    s['text']=''.join(chars)
                if not self.enabled:continue
                for i,s in enumerate(line['spans']):
                    if not s['font'].startswith('MT2') or not s['text'].strip():continue
                    # Script placement is relative to its nearby mathematical base,
                    # not the page's majority baseline (which fails for fractions).
                    bases=[b for b in line['spans'][:i] if b['font'].startswith('MT2')
                        and 'EXA' not in b['font'] and b['text'].strip()
                        and b['size']>s['size']*1.15 and 0<=s['bbox'][0]-b['bbox'][2]<16]
                    if not bases:continue
                    base=bases[-1];delta=s['origin'][1]-base['origin'][1]
                    if abs(delta)<1:continue
                    table=SUPER if delta<0 else SUB
                    text=s['text'].strip()
                    if not all(c in table and table[c]!='?' for c in text):continue
                    converted=''.join(table[c] for c in text)
                    s['text']=s['text'].replace(text,converted,1)
                    s['repairs'].append(dict(kind='superscript' if delta<0 else 'subscript',raw=text,text=converted,
                                             base_origin=list(base['origin']),origin=list(s['origin'])))
        return blocks
