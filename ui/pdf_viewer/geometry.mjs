export function highlightBox(viewport, sourceHeight, rectangle) {
  const [x1,y1]=viewport.convertToViewportPoint(rectangle[0],sourceHeight-rectangle[3]);
  const [x2,y2]=viewport.convertToViewportPoint(rectangle[2],sourceHeight-rectangle[1]);
  return {left:Math.min(x1,x2),top:Math.min(y1,y2),width:Math.abs(x2-x1),height:Math.abs(y2-y1)};
}

export function pdfHighlightBox(viewport, rectangle) {
  const [x1,y1]=viewport.convertToViewportPoint(rectangle[0],rectangle[1]);
  const [x2,y2]=viewport.convertToViewportPoint(rectangle[2],rectangle[3]);
  return {left:Math.min(x1,x2),top:Math.min(y1,y2),width:Math.abs(x2-x1),height:Math.abs(y2-y1)};
}
