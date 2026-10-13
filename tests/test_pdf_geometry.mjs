import assert from 'node:assert/strict';
import {highlightBox,pdfHighlightBox} from '../ui/pdf_viewer/geometry.mjs';
// Current PDF.js exposes point conversion. Top-left source boxes must survive zoom.
for (const scale of [0.5,1,2]) {
 const viewport={convertToViewportPoint:(x,y)=>[x*scale,(792-y)*scale]};
 assert.deepEqual(highlightBox(viewport,792,[100,120,500,150]),{left:100*scale,top:120*scale,width:400*scale,height:30*scale});
 const croppedViewport={convertToViewportPoint:(x,y)=>[(x-18)*scale,(792-y)*scale]};
 assert.deepEqual(pdfHighlightBox(croppedViewport,[118,642,518,672]),{left:100*scale,top:120*scale,width:400*scale,height:30*scale});
}
console.log('PDF highlight geometry passed at 50%, 100% and 200%.');
