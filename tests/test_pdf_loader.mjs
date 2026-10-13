import assert from 'node:assert/strict';
import {createPageLoader} from '../ui/pdf_viewer/document_loader.mjs';
let opened=0,closed=0;
// PDF.js 6 returns a proxy without destroy(); the loading task owns cleanup.
const loader=createPageLoader(data=>({promise:Promise.resolve({getPage:async n=>({number:n,bytes:data.length})}),destroy:async()=>{closed++;},id:++opened}));
const first=await loader({source_sha256:'book-a',source_page:38,pdf:'YQ=='});
const same=await loader({source_sha256:'book-a',source_page:38,pdf:'Yg=='});
assert.equal(same,first);assert.equal(opened,1);assert.equal(closed,0);
await loader({source_sha256:'book-b',source_page:38,pdf:'Yg=='});
assert.equal(opened,2);assert.equal(closed,1);
await loader({source_sha256:'book-b',source_page:47,pdf:'Yg=='});
assert.equal(opened,3);assert.equal(closed,2);
console.log('PDF page reuse and loading-task cleanup passed.');
