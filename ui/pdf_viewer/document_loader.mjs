export function createPageLoader(getDocument) {
  let loadingTask=null,sourceKey=null,page=null;
  return async function load(payload) {
    const key=payload.source_sha256+':'+payload.source_page;
    if(key===sourceKey&&page)return page;
    if(loadingTask)await loadingTask.destroy();
    sourceKey=null;page=null;
    const data=Uint8Array.from(atob(payload.pdf),c=>c.charCodeAt(0));
    loadingTask=getDocument(data);
    const document=await loadingTask.promise;
    page=await document.getPage(1);sourceKey=key;
    return page;
  };
}
