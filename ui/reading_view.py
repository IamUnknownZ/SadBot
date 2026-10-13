"""Escaped source text with a restrained reading layout."""
import html
import re


def reading_html(blocks):
    paragraphs=[]
    for block in blocks:
        escaped=html.escape(block)
        # Source metadata chooses code blocks in app.py. A variable such as m=i
        # or the words "For example" do not turn an explanation into code.
        escaped=re.sub(r'\[-?\d+(?:\.\d+)?(?:\s*,\s*-?\d+(?:\.\d+)?)*\]',lambda m:f'<code>{m[0]}</code>',escaped)
        paragraphs.append(f'<p>{escaped}</p>')
    return '<div class="source-reading">'+''.join(paragraphs)+'</div>'
