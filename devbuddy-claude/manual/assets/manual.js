(()=>{
  const d=document,r=d.documentElement,s=localStorage.getItem("devbuddy-theme");
  if(s)r.dataset.theme=s;
  d.querySelector("[data-theme]")?.addEventListener("click",()=>{
    const n=r.dataset.theme==="dark"?"light":"dark";
    r.dataset.theme=n;localStorage.setItem("devbuddy-theme",n);
  });
  d.querySelector("[data-menu]")?.addEventListener("click",e=>{
    const n=d.body.classList.toggle("sidebar-open");
    e.currentTarget.setAttribute("aria-expanded",String(n));
  });
  d.querySelectorAll(".copy").forEach(b=>b.addEventListener("click",async()=>{
    const c=b.closest(".code-wrap")?.querySelector("code")?.textContent||"";
    try{await navigator.clipboard.writeText(c);const o=b.textContent;b.textContent="Copied";setTimeout(()=>b.textContent=o,1200)}
    catch{b.textContent="Select manually"}
  }));
  const links=[...d.querySelectorAll(".sidebar a[data-page-title]")];
  d.querySelectorAll("[data-nav-filter]").forEach(f=>f.addEventListener("input",()=>{
    const q=f.value.toLowerCase();
    links.forEach(a=>a.hidden=!!q&&!a.dataset.pageTitle.toLowerCase().includes(q));
  }));
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
