const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const titles={chat:"Pregunta a tu conocimiento",search:"Encuentra lo que ya sabes",knowledge:"Biblioteca de conocimiento",memory:"Memoria controlada",graph:"Grafo de conocimiento",system:"Estado y arquitectura"};

async function api(path,opts={}){
  const r=await fetch(path,opts);
  let d={}; try{d=await r.json()}catch{}
  if(!r.ok) throw new Error(d.detail||`HTTP ${r.status}`);
  return d;
}
function toast(t,err=false){
  const e=$("#toast");e.textContent=t;e.className=err?"show error":"show";
  clearTimeout(window.tt);window.tt=setTimeout(()=>e.className="",3500);
}
function switchView(v){
  $$(".nav").forEach(b=>b.classList.toggle("active",b.dataset.view===v));
  $$(".view").forEach(x=>x.classList.toggle("active",x.id===`view-${v}`));
  $("#title").textContent=titles[v];
  if(v==="knowledge")loadDocs();
  if(v==="memory")loadMemory();
  if(v==="graph")loadGraph();
  if(v==="system")health();
}
$$(".nav").forEach(b=>b.onclick=()=>switchView(b.dataset.view));

async function health(){
  try{
    const h=await api("/api/health");
    $("#dot").classList.add("ok");
    $("#status").textContent="Sistema activo";
    $("#provider").textContent=`${h.provider} · ${h.chat_model}`;
    $("#docs").textContent=h.documents;
    $("#chunks").textContent=h.chunks;
    $("#vectors").textContent=h.vectors;
    $("#memories").textContent=h.memory_pending;
    const watcher=h.watcher||{};
    $("#info").innerHTML=[
      ["Versión",h.version],["Proveedor",h.provider],["Chat",h.chat_model],
      ["Embeddings",h.embedding_model],["Ollama",h.ollama?"conectado":"no disponible"],
      ["Auto-index",h.auto_index?"activo":"desactivado"],["Watch interval",`${h.watch_interval_seconds}s`],
      ["Último scan",watcher.last_scan||"pendiente"],["Documentos",h.documents],
      ["Fragmentos",h.chunks],["Vectores",h.vectors],["Memorias pendientes",h.memory_pending]
    ].map(x=>`<dt>${esc(x[0])}</dt><dd>${esc(x[1])}</dd>`).join("");
  }catch(e){
    $("#status").textContent="Sin conexión";
    $("#provider").textContent=e.message;
  }
}

function message(role,text,sources=[]){
  const row=document.createElement("div");row.className=`msg ${role}`;
  const av=document.createElement("i");av.textContent=role==="user"?"YOU":"404";
  const b=document.createElement("div");b.textContent=text;
  if(sources.length){
    const s=document.createElement("div");s.className="sources";
    s.innerHTML="<b>Fuentes</b><br>"+sources.map(x=>`${esc(x.ref)} · ${esc(x.path)} · ${esc(x.locator)}`).join("<br>");
    b.appendChild(s);
  }
  row.append(av,b);$("#chat").appendChild(row);$("#chat").scrollTop=$("#chat").scrollHeight;
  return b;
}

$("#chatForm").onsubmit=async e=>{
  e.preventDefault();
  const q=$("#question").value.trim();if(!q)return;
  message("user",q);$("#question").value="";
  const wait=message("ai","Consultando tu conocimiento…");
  try{
    const d=await api("/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question:q})});
    wait.textContent=d.answer;
    if(d.sources?.length){
      const s=document.createElement("div");s.className="sources";
      s.innerHTML="<b>Fuentes</b><br>"+d.sources.map(x=>`${esc(x.ref)} · ${esc(x.path)} · ${esc(x.locator)}`).join("<br>");
      wait.appendChild(s);
    }
    setTimeout(health,1500);
  }catch(x){wait.textContent=`Error: ${x.message}`}
};

$("#searchForm").onsubmit=async e=>{
  e.preventDefault();const box=$("#results");box.innerHTML="<div class='result'>Buscando…</div>";
  try{
    const d=await api("/api/search",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({query:$("#query").value,top_k:10})});
    box.innerHTML=d.items.length?d.items.map(x=>`<article class="result"><div class="row"><strong>${esc(x.title)} · ${esc(x.locator)}</strong><span class="score">${Math.round(x.score*100)}%</span></div><p>${esc(x.text.slice(0,600))}${x.text.length>600?"…":""}</p><div class="meta">${esc(x.path)} · ${esc(x.source_area)}</div></article>`).join(""):"<div class='result'>Sin resultados.</div>";
  }catch(x){box.innerHTML=`<div class='result'>Error: ${esc(x.message)}</div>`}
};

async function loadDocs(){
  const box=$("#documents");box.innerHTML="<div class='doc'>Cargando…</div>";
  try{
    const d=await api("/api/documents?limit=200");
    box.innerHTML=d.items.length?d.items.map(x=>`<div class="doc"><div><strong>${esc(x.title)}</strong><small>${esc(x.path)}</small></div><em>${esc(x.source_area)}</em></div>`).join(""):"<div class='doc'>No hay documentos indexados.</div>";
  }catch(x){box.innerHTML=`<div class='doc'>Error: ${esc(x.message)}</div>`}
}
$("#refresh").onclick=loadDocs;

async function loadMemory(){
  const box=$("#memoryList");box.innerHTML="<div class='memory-card'>Cargando…</div>";
  try{
    const d=await api("/api/memory/candidates?status=pending");
    if(!d.items.length){
      box.innerHTML="<div class='memory-card'>No hay memorias pendientes. Las propuestas aparecen aquí después de conversaciones que contengan decisiones o preferencias duraderas.</div>";
      return;
    }
    box.innerHTML=d.items.map(x=>`<article class="memory-card" data-id="${x.id}"><span class="tag">${esc(x.category)}</span><h3>${esc(x.title)}</h3><p>${esc(x.content)}</p><div class="meta">${esc(x.created_at)}</div><div class="memory-actions"><button class="approve" data-action="approve" data-id="${x.id}">Guardar memoria</button><button class="reject" data-action="reject" data-id="${x.id}">Descartar</button></div></article>`).join("");
  }catch(x){box.innerHTML=`<div class='memory-card'>Error: ${esc(x.message)}</div>`}
}
$("#refreshMemory").onclick=loadMemory;
$("#memoryList").onclick=async e=>{
  const btn=e.target.closest("button[data-action]");if(!btn)return;
  const id=btn.dataset.id, action=btn.dataset.action;
  btn.disabled=true;
  try{
    if(action==="approve"){
      const d=await api(`/api/memory/candidates/${id}/approve`,{method:"POST"});
      toast(`Memoria guardada en ${d.path}`);
    }else{
      await api(`/api/memory/candidates/${id}/reject`,{method:"POST"});
      toast("Memoria descartada");
    }
    await loadMemory();await health();
  }catch(x){toast(x.message,true);btn.disabled=false}
};

let graphData=null;
async function loadGraph(){
  $("#graphMeta").textContent="Cargando grafo…";
  try{
    graphData=await api("/api/graph");
    $("#graphMeta").textContent=`${graphData.node_count} notas · ${graphData.edge_count} enlaces · ${graphData.unresolved.length} enlaces sin resolver`;
    drawGraph(graphData);
  }catch(x){$("#graphMeta").textContent=`Error: ${x.message}`}
}
$("#refreshGraph").onclick=loadGraph;

function drawGraph(data){
  const canvas=$("#graphCanvas"), ctx=canvas.getContext("2d");
  const rect=canvas.getBoundingClientRect(), dpr=Math.min(window.devicePixelRatio||1,2);
  canvas.width=Math.max(800,Math.floor(rect.width*dpr));
  canvas.height=Math.max(500,Math.floor(rect.height*dpr));
  ctx.setTransform(dpr,0,0,dpr,0,0);
  const w=canvas.width/dpr,h=canvas.height/dpr;
  ctx.clearRect(0,0,w,h);

  const nodes=data.nodes.slice(0,250);
  const ids=new Set(nodes.map(n=>n.id));
  const edges=data.edges.filter(e=>ids.has(e.source)&&ids.has(e.target));
  const groups=[...new Set(nodes.map(n=>n.area))];
  const pos=new Map();

  groups.forEach((g,gi)=>{
    const list=nodes.filter(n=>n.area===g);
    const cx=(gi+1)*w/(groups.length+1);
    const cy=h/2;
    const radius=Math.min(140,Math.max(55,list.length*5));
    list.forEach((n,i)=>{
      const a=(Math.PI*2*i/Math.max(1,list.length))-(Math.PI/2);
      const r=list.length===1?0:radius*(0.72+0.28*((i%3)/2));
      pos.set(n.id,{x:cx+Math.cos(a)*r,y:cy+Math.sin(a)*r});
    });
  });

  ctx.lineWidth=1;ctx.strokeStyle="rgba(142,154,165,.24)";
  edges.forEach(e=>{
    const a=pos.get(e.source),b=pos.get(e.target);if(!a||!b)return;
    ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();
  });

  nodes.forEach(n=>{
    const p=pos.get(n.id);if(!p)return;
    const r=4+Math.min(8,n.degree||0);
    ctx.beginPath();ctx.fillStyle=n.area==="40_MEMORY"?"#d7ff3f":"#dce4ea";
    ctx.arc(p.x,p.y,r,0,Math.PI*2);ctx.fill();
    if(n.degree>0){
      ctx.fillStyle="#9aa6b2";ctx.font="11px system-ui";
      ctx.fillText(n.label.slice(0,22),p.x+r+4,p.y+4);
    }
  });

  ctx.fillStyle="#7f8b96";ctx.font="12px system-ui";
  groups.forEach((g,gi)=>{
    const cx=(gi+1)*w/(groups.length+1);
    ctx.fillText(g,cx-35,22);
  });
}

window.addEventListener("resize",()=>{if(graphData&&$("#view-graph").classList.contains("active"))drawGraph(graphData)});

async function poll(id){
  while(true){
    const j=await api(`/api/jobs/${id}`);
    $("#activity").textContent=JSON.stringify(j,null,2);
    if(j.status==="done"){
      toast(`Indexación: ${j.result.indexed} procesados, ${j.result.skipped} sin cambios, ${j.result.removed} eliminados.`);
      await health();return;
    }
    if(j.status==="error")throw new Error(j.error||"Error");
    await new Promise(r=>setTimeout(r,900));
  }
}
$("#index").onclick=async()=>{
  const b=$("#index");b.disabled=true;b.textContent="Indexando…";
  try{
    const j=await api("/api/index",{method:"POST"});
    await poll(j.job_id);
  }catch(x){toast(x.message,true)}
  finally{b.disabled=false;b.textContent="Reindexar"}
};

$("#file").onchange=async()=>{
  const f=$("#file").files[0];if(!f)return;
  const fd=new FormData();fd.append("file",f);
  try{
    toast("Subiendo…");
    const d=await api("/api/upload",{method:"POST",body:fd});
    toast(d.message);
    setTimeout(health,3000);
  }catch(x){toast(x.message,true)}
  finally{$("#file").value=""}
};

health();
setInterval(health,30000);
