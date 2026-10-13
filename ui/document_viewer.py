"""Render precise evidence coordinates without changing the original PDF."""
from functools import lru_cache
from pathlib import Path
import pymupdf
from services.ingest import safe_path
from ui.evidence_groups import highlight_regions


def evidence_preview(root,document,evidence):
    source=safe_path(Path(root),document['file'])
    with pymupdf.open(source) as pdf:
        page=pdf[evidence['page']-1]
        for box in highlight_regions(evidence['lines']):
            annotation=page.add_rect_annot(pymupdf.Rect(box))
            annotation.set_colors(stroke=(1,.82,.22),fill=(1,.82,.22))
            annotation.set_border(width=0);annotation.set_opacity(.35);annotation.update()
        rect=pymupdf.Rect(evidence['bbox'])
        clip=pymupdf.Rect(max(0,rect.x0-18),max(0,rect.y0-18),min(page.rect.width,rect.x1+18),min(page.rect.height,rect.y1+18))
        preview=page.get_pixmap(matrix=pymupdf.Matrix(1.6,1.6),clip=clip,alpha=False).tobytes('png')
        with pymupdf.open() as selected:
            selected.insert_pdf(pdf,from_page=evidence['page']-1,to_page=evidence['page']-1,annots=True)
            single_page=selected.tobytes()
    return preview,single_page


def pdf_payload(root,data,evidence):
    """Transfer one original PDF page, with source-space highlight boxes separately."""
    import base64
    source=safe_path(Path(root),data['document']['file'])
    with pymupdf.open(source) as pdf, pymupdf.open() as selected:
        page=pdf[evidence['page']-1]
        selected.insert_pdf(pdf,from_page=evidence['page']-1,to_page=evidence['page']-1,annots=False)
        blob=selected.tobytes(garbage=4,deflate=True)
        lines=[l for l in data['pages'][evidence['page']-1]['lines'] if l['id'] in evidence['line_ids']]
        regions=highlight_regions(lines)
        return dict(pdf=base64.b64encode(blob).decode(),source_page=evidence['page'],
                    source_name=Path(data['document']['file']).name,source_sha256=data['document']['sha256'],
                    width=page.rect.width,height=page.rect.height,
                    rectangles=regions,
                    # PyMuPDF text uses top-left coordinates relative to the crop.
                    # PDF.js expects PDF user space, including the MediaBox offset.
                    pdf_rectangles=[list(pymupdf.Rect(box)*~page.transformation_matrix) for box in regions],
                    line_ids=[l['id'] for l in lines])


def show_pdf(payload,key):
    import streamlit.components.v1 as components
    component=components.declare_component('source_pdf',path=str(Path(__file__).parent/'pdf_viewer'))
    return component(payload=payload,key=key,default=None)
