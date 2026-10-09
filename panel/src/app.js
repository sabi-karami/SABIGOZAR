// SABIGOZAR Deploy Panel browser logic
export default `(function(){
"use strict";
var $=function(i){return document.getElementById(i)};
var KEY=sessionStorage.getItem("sgp-key")||"";
var NAMES={check:"بررسی کلیدها و دامنه",github:"GitHub: فورک / همگام‌سازی ریپو",railway:"Railway: پروژه، سرویس و متغیرها (نام کاربری/رمز)",settings:"Railway: Volume، Health Check، Restart، منطقه",domains:"Railway: دامنه، TCP Proxy (Reality)، دامنه‌ی شخصی",cloudflare:"Cloudflare: CNAME نارنجی، TXT، SSL Full، WebSockets",deploy:"Railway: Deploy آخرین نسخه",wait:"منتظر Deploy و گواهی SSL",verify:"تست کامل: ورود، کاربر تست، لینک ساب",report:"گزارش نهایی"};
var ORDER=["check","github","railway","settings","domains","cloudflare","deploy","wait","verify","report"];
var FIELDS=["railwayToken","cfToken","ghToken","domain","adminUser","adminPass","repo","sourceRepo","region","cleanIps","project","service","workspace","testUser","deleteDns","extraVars"];
var SAVE=["domain","adminUser","repo","sourceRepo","region","cleanIps","project","service","workspace","testUser"];
var ST={},LOG=[],running=false;
function toast(t){var e=$("toast");e.textContent=t;e.classList.add("on");clearTimeout(e._t);e._t=setTimeout(function(){e.classList.remove("on")},1800)}
function copy(t){if(navigator.clipboard)navigator.clipboard.writeText(t).then(function(){toast("کپی شد ✓")});else{var a=document.createElement("textarea");a.value=t;document.body.appendChild(a);a.select();document.execCommand("copy");a.remove();toast("کپی شد ✓")}}
function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){return"&#"+c.charCodeAt(0)+";"})}
function api(step,body){return fetch("/api/"+step,{method:"POST",headers:{"Content-Type":"application/json","x-panel-key":KEY},body:JSON.stringify(body||{})}).then(function(r){return r.json().catch(function(){return{ok:false,error:"HTTP "+r.status}}).then(function(j){j.status=r.status;return j})})}

/* login */
function showApp(){$("lockV").classList.add("hide");$("appV").classList.remove("hide");var s={};try{s=JSON.parse(localStorage.getItem("sgp-form")||"{}")}catch(e){}SAVE.forEach(function(k){if(s[k]!==undefined&&$(k))$(k).value=s[k]});if(!$("domain").value)$("domain").value="sabigozar."+location.hostname.split(".").slice(-2).join(".")}
function login(){KEY=$("pk").value;$("loginB").disabled=true;api("login").then(function(j){$("loginB").disabled=false;if(j.ok){sessionStorage.setItem("sgp-key",KEY);showApp()}else $("loginE").textContent=j.error==="auth"?"رمز اشتباه است.":j.error})}
$("loginB").onclick=login;$("pk").onkeydown=function(e){if(e.key==="Enter")login()};
if(KEY)api("login").then(function(j){if(j.ok)showApp();else sessionStorage.removeItem("sgp-key")});

/* steps ui */
function drawSteps(cur,state){$("steps").innerHTML=ORDER.map(function(k,i){var c=state[k]||"";return'<div class="st '+c+'"><i>'+(c==="ok"?"✓":c==="err"?"✕":c==="warn"?"!":i+1)+"</i><span>"+NAMES[k]+'</span><small id="t-'+k+'"></small></div>'}).join("");var done=ORDER.filter(function(k){return state[k]==="ok"||state[k]==="warn"}).length;$("barB").style.width=Math.round(done/ORDER.length*100)+"%"}
function log(t,l){LOG.push({t:t,l:l||"info"});var e=document.createElement("div");e.className=l||"info";e.textContent=t;$("log").appendChild(e);$("log").scrollTop=1e9}
function inp(){var o={};FIELDS.forEach(function(k){o[k]=($(k).value||"").trim()});o.dnsOnly=$("dnsOnly").checked;o.panelHost=location.hostname;return o}

function run(){if(running)return;var I=inp();if(!I.railwayToken||!I.cfToken||!I.domain){toast("Railway Token، Cloudflare Token و دامنه لازم است");return}
if(I.domain===location.hostname){toast("دامنه‌ی VPN نباید همان آدرس این پنل باشد");return}
var s={};SAVE.forEach(function(k){s[k]=I[k]});try{localStorage.setItem("sgp-form",JSON.stringify(s))}catch(e){}
running=true;ST={panelHost:location.hostname};LOG=[];$("log").innerHTML="";$("goB").disabled=true;$("progC").classList.remove("hide");$("repC").classList.add("hide");
var state={},skip=$("skipDeploy").checked,t0=Date.now();drawSteps(null,state);
var i=0,polls=0;
(function next(){if(i>=ORDER.length){finish(true);return}var k=ORDER[i];
if(skip&&k==="deploy"){state[k]="warn";log("— Deploy دوباره انجام نشد (طبق انتخاب تو)","warn");i++;drawSteps(k,state);return next()}
state[k]="run";drawSteps(k,state);if(k!=="wait"||!polls)log("▶ "+NAMES[k],"h");var ts=Date.now();
api(k,{inp:I,st:ST}).then(function(j){(j.logs||[]).forEach(function(x){log(x.t,x.l)});
if(j.status===401){log("نشست پنل منقضی شد؛ دوباره وارد شو.","err");sessionStorage.removeItem("sgp-key");state[k]="err";drawSteps(k,state);return finish(false)}
if(!j.ok){state[k]="err";drawSteps(k,state);log("✕ "+(j.error||"error"),"err");return finish(false,k)}
ST=j.st||ST;
if(k==="wait"&&!ST.done){polls++;if(Date.now()-t0>25*60*1000){state[k]="err";drawSteps(k,state);log("✕ زمان انتظار تمام شد. چند دقیقه بعد دوباره اجرا کن؛ چیزی تکراری ساخته نمی‌شود.","err");return finish(false,k)}var el=$("t-wait");if(el)el.textContent=Math.round((Date.now()-t0)/1000)+"s";return setTimeout(next,10000)}
state[k]=(j.logs||[]).some(function(x){return x.l==="warn"})?"warn":"ok";drawSteps(k,state);var e2=$("t-"+k);if(e2)e2.textContent=((Date.now()-ts)/1000).toFixed(1)+"s";i++;next()}).catch(function(e){state[k]="err";drawSteps(k,state);log("✕ خطای شبکه: "+e,"err");finish(false,k)})})()}
$("goB").onclick=run;$("agB").onclick=function(){$("repC").classList.add("hide");scrollTo({top:0,behavior:"smooth"});run()};

/* report */
var REP="";
function kv(k,v,secret){var id="r"+Math.random().toString(36).slice(2);return'<div class="kv"><b>'+esc(k)+'</b><code id="'+id+'" data-v="'+esc(v)+'"'+(secret?' data-s="1">••••••••••':">"+esc(v))+"</code><span>"+(secret?'<button data-show="'+id+'">نمایش</button> ':"")+'<button data-cp="'+id+'">کپی</button></span></div>'}
function finish(ok,failed){running=false;$("goB").disabled=false;$("repC").classList.remove("hide");var s=ST,R=[],h="";
h+=ok?'<div class="note ok">✅ نصب کامل شد و همه‌ی تست‌ها رد شدند.</div>':'<div class="note bad">❌ کار در مرحله‌ی «'+esc(NAMES[failed]||failed||"")+'» متوقف شد. خطا را در لاگ بالا ببین، مشکل را حل کن و دوباره اجرا کن؛ چیزی تکراری ساخته نمی‌شود.</div>';
var rows=[["آدرس پنل VPN",s.domain?"https://"+s.domain+"/dashboard/":""],["نام کاربری",s.adminUser],["رمز",s.adminPass,1],["منبع رمز",{generated:"ساخته‌شده خودکار (در Railway ← Variables)",yours:"رمز خودت",kept:"رمز قبلی حفظ شد"}[s.pwSource]],["Railway · اکانت",s.email],["Railway · Workspace",s.wsName],["Railway · پروژه / سرویس",s.project?s.project+" / "+s.service:""],["ریپوی GitHub",s.repo?s.repo+(s.commit?" @ "+s.commit:""):""],["منطقه",s.region],["Volume",s.volume],["دامنه‌ی Railway",s.railwayDomain],["Reality (TCP Proxy)",s.tcp],["Cloudflare · Zone",s.zone],["Cloudflare · CNAME",s.cname?s.domain+" → "+s.cname+(document.getElementById("dnsOnly").checked?"":" (🟠 Proxied)"):""],["Cloudflare · TXT",s.txtHost||""],["Cloudflare · SSL / WebSockets",s.ssl?s.ssl+" / "+s.ws:""],["رکوردهای پاک‌شده",(s.deleted||[]).join("، ")],["Deploy",s.deployedCommit?"SUCCESS · commit "+s.deployedCommit:s.depId?"SUCCESS":""],["کانفیگ‌ها",(s.configs||[]).length?(s.configs.length+" عدد"):""],["کاربر تست",s.testUser],["لینک ساب کاربر تست",s.testSub,1]];
rows.forEach(function(r){if(r[1]){h+=kv(r[0],r[1],r[2]);R.push(r[0]+": "+r[1])}});
if((s.configs||[]).length)h+='<div class="kv" style="grid-template-columns:1fr"><b>لیست کانفیگ‌ها</b><code>'+s.configs.map(esc).join("<br>")+"</code></div>";
h+='<div class="note">📌 <b>بعد از نصب:</b><br>• در Railway ← Workspace Settings ← Usage یک سقف هزینه بگذار.<br>• رمز پنل همیشه در Railway ← Variables ← <code>ADMIN_PASSWORD</code> هست.<br>• اگر کانفیگ‌های ☁️ CDN کند بودند، IP تمیز دیگری بگذار و دوباره اجرا کن.<br>• توکن‌هایی که دیگر لازم نداری را باطل کن.<br>• قوانین Railway پروکسی و فروش دوباره را ممنوع کرده؛ ممکن است سرویس بسته شود.</div>';
$("rep").innerHTML=h;
REP="SABIGOZAR · گزارش نصب\\n"+new Date().toLocaleString("fa-IR")+"\\nوضعیت: "+(ok?"موفق":"ناتمام ("+(NAMES[failed]||failed)+")")+"\\n\\n"+R.join("\\n")+((s.configs||[]).length?"\\n\\nکانفیگ‌ها:\\n"+s.configs.join("\\n"):"")+"\\n\\n── لاگ کامل ──\\n"+LOG.map(function(x){return x.t}).join("\\n")+"\\n";
$("repC").scrollIntoView({behavior:"smooth"})}
$("rep").onclick=function(e){var b=e.target.closest("button");if(!b)return;var c=$(b.getAttribute("data-cp")||b.getAttribute("data-show"));if(b.hasAttribute("data-cp"))copy(c.getAttribute("data-v"));else{var sh=c.getAttribute("data-s")==="1";c.textContent=sh?c.getAttribute("data-v"):"••••••••••";c.setAttribute("data-s",sh?"0":"1");b.textContent=sh?"مخفی":"نمایش"}};
$("cpR").onclick=function(){copy(REP)};
$("dlR").onclick=function(){var a=document.createElement("a");a.href=URL.createObjectURL(new Blob([REP],{type:"text/plain"}));a.download="SABIGOZAR-report-"+new Date().toISOString().slice(0,10)+".txt";a.click()};
})();
`;
