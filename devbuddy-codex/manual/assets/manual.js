(()=>{
  const d=document,r=d.documentElement,s=localStorage.getItem("devbuddy-theme");
  if(s)r.dataset.theme=s;
  const th=r.lang==="th", labels=th?{search:"ค้นหาเอกสาร",filter:"กรองหน้า",noResults:"ไม่พบหน้าที่ตรงกัน",open:"เปิดเมนู",close:"ปิดเมนู",dark:"เปลี่ยนเป็นโหมดมืด",light:"เปลี่ยนเป็นโหมดสว่าง",on:"โหมดมืดเปิดอยู่",off:"โหมดสว่างเปิดอยู่"}:{search:"Search documentation",filter:"Filter pages",noResults:"No matching pages",open:"Open navigation",close:"Close navigation",dark:"Switch to dark mode",light:"Switch to light mode",on:"Dark mode is on",off:"Light mode is on"};
  const actions=d.querySelector(".header-actions"),header=d.querySelector(".site-header");
  if(actions&&!actions.querySelector("[data-theme]")){const b=d.createElement("button");b.className="icon-button";b.dataset.theme="";b.textContent="◐";actions.append(b)}
  if(actions&&!actions.querySelector("[data-menu]")){const b=d.createElement("button");b.className="icon-button mobile-only";b.dataset.menu="";b.textContent="☰";actions.append(b)}
  if(actions&&!actions.querySelector("[data-nav-filter]")){const l=d.createElement("label");l.className="header-search";l.innerHTML='<span class="sr-only">Search</span><input type="search" data-nav-filter>';actions.insertBefore(l,actions.firstChild)}
  const theme=d.querySelector("[data-theme]");
  const updateTheme=()=>{if(!theme)return;const dark=r.dataset.theme==="dark";theme.setAttribute("aria-pressed",String(dark));theme.setAttribute("aria-label",dark?labels.light:labels.dark);theme.title=dark?labels.on:labels.off};
  updateTheme();
  theme?.addEventListener("click",()=>{
    const n=r.dataset.theme==="dark"?"light":"dark";
    r.dataset.theme=n;localStorage.setItem("devbuddy-theme",n);
    updateTheme();
  });
  const menu=d.querySelector("[data-menu]"),sidebar=d.querySelector(".sidebar");
  let backdrop=d.querySelector(".nav-backdrop");
  if(menu&&sidebar&&!backdrop){backdrop=d.createElement("div");backdrop.className="nav-backdrop";backdrop.setAttribute("aria-hidden","true");d.body.append(backdrop)}
  let lastFocus;
  const close=()=>{if(!menu)return;d.body.classList.remove("sidebar-open");d.body.style.overflow="";menu.setAttribute("aria-expanded","false");menu.setAttribute("aria-label",labels.open);lastFocus?.focus()};
  menu?.addEventListener("click",e=>{const open=!d.body.classList.contains("sidebar-open");if(open){lastFocus=e.currentTarget;d.body.classList.add("sidebar-open");d.body.style.overflow="hidden";e.currentTarget.setAttribute("aria-expanded","true");e.currentTarget.setAttribute("aria-label",labels.close);sidebar?.querySelector("input,a")?.focus()}else close()});
  backdrop?.addEventListener("click",close);d.addEventListener("keydown",e=>{if(e.key==="Escape"&&d.body.classList.contains("sidebar-open"))close()});
  d.querySelectorAll(".copy").forEach(b=>b.addEventListener("click",async()=>{
    const c=b.closest(".code-wrap")?.querySelector("code")?.textContent||"";
    try{await navigator.clipboard.writeText(c);const o=b.textContent;b.textContent="Copied";setTimeout(()=>b.textContent=o,1200)}
    catch{b.textContent="Select manually"}
  }));
  const links=[...d.querySelectorAll(".sidebar a")];
  const sidebarNav=sidebar?.querySelector(".nav-group");
  if(sidebarNav){
    const pages=[['index.html','Overview'],['getting-started.html','Getting started'],['workspace.html','Workspace'],['scripts.html','Scripts'],['tasks-and-knowledge.html','Tasks & knowledge'],['migration.html','Migration'],['troubleshooting.html','Troubleshooting'],['plugin-first.html','Plugin-first'],['git-install.html','Install & migration'],['database-profiles.html','Database profiles']];
    pages.forEach(([href,label])=>{if(!sidebar.querySelector(`a[href="${href}"]`)){const a=d.createElement('a');a.href=href;a.textContent=label;if(location.pathname.endsWith('/'+href))a.setAttribute('aria-current','page');sidebarNav.append(a)}});
  }
  const refreshedLinks=[...d.querySelectorAll(".sidebar a")];
  links.splice(0,links.length,...refreshedLinks);
  links.forEach(a=>{if(!a.dataset.pageTitle)a.dataset.pageTitle=a.textContent.trim()});
  const filters=[...d.querySelectorAll("[data-nav-filter]")],status=d.createElement("p");status.className="search-empty";status.textContent=labels.noResults;status.hidden=true;sidebar?.append(status);
  filters.forEach(f=>{f.placeholder=f.classList.contains("sidebar-search")?labels.filter:labels.search;f.setAttribute("aria-label",f.classList.contains("sidebar-search")?labels.filter:labels.search);f.addEventListener("input",()=>{const q=f.value.trim().toLowerCase();filters.forEach(other=>{if(other!==f)other.value=f.value});let shown=0;links.forEach(a=>{const current=a.getAttribute("aria-current")==="page";const match=!q||current||a.dataset.pageTitle.toLowerCase().includes(q);a.hidden=!match;if(match)shown++});status.hidden=shown>0||!q})});
  links.forEach(a=>a.addEventListener("click",()=>{if(d.body.classList.contains("sidebar-open"))close()}));
  const ls=[...d.querySelectorAll(".toc a")],hs=ls.map(a=>d.getElementById(a.getAttribute("href").slice(1))).filter(Boolean);
  if("IntersectionObserver"in window){
    const io=new IntersectionObserver(es=>es.forEach(e=>{
      if(e.isIntersecting)ls.forEach(a=>a.classList.toggle("active",a.getAttribute("href")==="#"+e.target.id));
    }),{rootMargin:"-15% 0px -70%"});
    hs.forEach(h=>io.observe(h));
  }
  if(!d.querySelector('.header-nav a[href="database-profiles.html"]')){
    const nav=d.querySelector(".header-nav"),link=d.createElement("a");
    link.href="database-profiles.html";
    link.textContent=r.lang==="th"?"Database Profile":"Database profiles";
    nav?.append(link);
  }
  const openCodeRow=[...d.querySelectorAll("#distribution tbody tr")].find(row=>row.cells[0]?.textContent.trim()==="OpenCode");
  if(openCodeRow){
    const thai=r.lang==="th";
    openCodeRow.cells[1].innerHTML=thai?'<code class="inline">opencode</code> profile / package จาก Git subdirectory':'<code class="inline">opencode</code> profile / Git subdirectory package';
    openCodeRow.cells[3].textContent=thai?"ติดตั้งจาก Git package ที่ pin แล้วใช้ workflow native ของ host":"Install the pinned Git package, then use the host-native workflow";
  }
})();
