// 镜像 index.html 的数据与检索逻辑，验证搜索结果
const KG = {
  "英伟达":{market:"美股",alias:["NVDA","Nvidia"],affects:[["300308","中际旭创","通信设备","产业链下游","GPU算力扩张拉动800G/1.6T光模块需求"],["300502","新易盛","通信设备","产业链下游","同属AI光模块核心供应商"],["300394","天孚通信","通信设备","产业链下游","光器件配套英伟达算力链"],["002384","东山精密","电子制造","供应商客户","PCB/精密制造供应AI服务器链"]]},
  "AMD":{market:"美股",alias:["AMD","超威"],affects:[["688256","寒武纪","半导体","国产替代","AMD GPU对标产品，国产AI芯片替代逻辑"],["603986","兆易创新","半导体","国产替代","存储/MCU国产替代受益"]]},
  "美光":{market:"美股",alias:["MU","Micron"],affects:[["603986","兆易创新","半导体","国产替代","美光受限制则国产存储替代加速"],["300223","北京君正","半导体","国产替代","车规/利基存储国产替代"]]},
  "海力士":{market:"日韩",alias:["SK Hynix","海力士"],affects:[["603986","兆易创新","半导体","概念板块","HBM/存储涨价周期带动存储板块"],["688008","澜起科技","半导体","概念板块","存储接口芯片受益"]]},
  "三星":{market:"日韩",alias:["Samsung","三星"],affects:[["000725","京东方A","面板","同业竞争","面板价格与产能联动"],["603986","兆易创新","半导体","概念板块","存储芯片涨价指引利好板块"]]},
  "英特尔":{market:"美股",alias:["INTC","Intel"],affects:[["688256","寒武纪","半导体","国产替代","x86弱势利好国产CPU/GPU"],["603986","兆易创新","半导体","国产替代","国产芯片替代逻辑"]]},
  "康宁":{market:"美股",alias:["GLW","Corning"],affects:[["300433","蓝思科技","电子制造","供应商客户","玻璃基板/盖板供需联动"]]},
  "长江存储":{market:"概念",alias:["YMTC"],affects:[["603986","兆易创新","半导体","概念板块","长江存储扩产利好存储芯片概念"],["300223","北京君正","半导体","概念板块","存储国产化概念"]]},
  "长鑫存储":{market:"概念",alias:["CXMT"],affects:[["603986","兆易创新","半导体","概念板块","长鑫DRAM国产替代概念"],["688008","澜起科技","半导体","概念板块","DRAM接口芯片配套"]]},
  "特斯拉":{market:"美股",alias:["Tesla","TSLA"],affects:[["601689","拓普集团","汽车零部件","供应商客户","特斯拉链零部件供应"],["002050","三花智控","汽车零部件","供应商客户","热管理配套特斯拉"]]},
  "东京电子":{market:"日韩",alias:["TEL"],affects:[["688012","中微公司","半导体设备","国产替代","对华设备限制加码，国产替代提速"],["002371","北方华创","半导体设备","国产替代","半导体设备国产化逻辑"]]},
  "中际旭创":{market:"A股",alias:["300308"],affects:[["300308","中际旭创","通信设备","直接","事件主体即为A股标的"]]},
  "东山精密":{market:"A股",alias:["002384"],affects:[["002384","东山精密","电子制造","直接","事件主体即为A股标的"]]},
  "寒武纪":{market:"A股",alias:["688256"],affects:[["688256","寒武纪","半导体","直接","事件主体即为A股标的"]]},
  "兆易创新":{market:"A股",alias:["603986"],affects:[["603986","兆易创新","半导体","直接","事件主体即为A股标的"]]},
};
const CONCEPT = {
  "存储芯片":[["603986","兆易创新"],["300223","北京君正"],["688008","澜起科技"]],
  "算力/CPO":[["300308","中际旭创"],["300502","新易盛"],["300394","天孚通信"]],
  "半导体设备":[["688012","中微公司"],["002371","北方华创"]],
  "面板":[["000725","京东方A"]],
  "玻璃基板":[["300433","蓝思科技"]],
  "PCB":[["002384","东山精密"],["002916","深南电路"]],
  "券商":[["600030","中信证券"],["601211","国泰君安"]],
  "黄金":[["600547","山东黄金"],["002155","湖南黄金"]],
};
const SENTI_RULES = [
  ["利好",["创新高","超预期","大涨","利好","获大单","扩产","上调","中标","突破","满产","涨价","补贴","扶持"]],
  ["利空",["制裁","暴跌","不及预期","裁员","减产","下调","亏损","限制","收紧"]],
  ["中性偏利好",["略超预期","小幅增长","温和回暖","偏正面","略好于"]],
  ["中性偏利空",["略不及预期","小幅下滑","温和承压","偏负面","略弱于"]],
  ["中性",["符合预期","平稳","维持","不变","中性","持平"]],
];
function classify(text){for(const[t,kws]of SENTI_RULES){for(const kw of kws){if(text.includes(kw))return{tier:t,conf:(t==="利好"||t==="利空")?0.85:(t.includes("偏")?0.7:0.6)};}}return{tier:"中性",conf:0.55};}
function mapAffected(title,body){const text=title+" "+(body||"");const out={};const add=(code,name,sector,rel,reason,conf)=>{if(!out[code])out[code]={code,name,sector,relation:rel,reasons:[reason],conf};else{out[code].reasons.push(reason);out[code].conf=Math.min(1,out[code].conf+0.1);}};
  for(const name in KG){const node=KG[name];const hit=text.includes(name)||node.alias.some(a=>text.includes(a));if(hit){node.affects.forEach(([code,name2,sector,rel,reason])=>{const conf=rel==="直接"?1.0:(rel==="产业链下游"||rel==="供应商客户")?0.8:0.6;add(code,name2,sector,rel,reason,conf);});for(const c in CONCEPT){if(text.includes(c))CONCEPT[c].forEach(([code,name2])=>add(code,name2,"概念板块","概念板块","事件涉及「"+c+"」板块",0.6));}}}
  const res=Object.values(out).map(v=>({...v,reason:v.reasons.slice(0,2).join("；")}));res.sort((a,b)=>b.conf-a.conf);return res;}
const EVENTS=[
  {market:"美股",cat:"海外市场",title:"英伟达数据中心收入创新高，上调全年指引",body:"Blackwell 量产顺利，云厂商资本开支持续扩张。"},
  {market:"美股",cat:"企业公告",title:"美光遭某国出口限制，存储供给收紧",body:"部分市场供货受限，行业供需预期改善。"},
  {market:"日韩",cat:"企业公告",title:"三星电子存储芯片涨价指引超预期",body:"DRAM 合约价上调，行业景气度回升。"},
  {market:"日韩",cat:"财经快讯",title:"海力士 HBM 产能满载，上调资本开支",body:"AI 服务器需求拉动 HBM 供不应求。"},
  {market:"A股",cat:"企业公告",title:"中际旭创发布超预期财报，光模块出货高增",body:"800G 产品放量，毛利率持续改善。"},
  {market:"A股",cat:"企业公告",title:"某光伏企业宣布减产以稳价格",body:"行业产能出清，价格有望企稳。"},
  {market:"美股",cat:"投研报告",title:"AMD 发布新 GPU 对标英伟达，生态扩张",body:"MI 系列迭代，算力竞争格局生变。"},
  {market:"美股",cat:"财经快讯",title:"英特尔宣布大规模裁员，战略收缩",body:"聚焦代工与 AI，传统业务承压。"},
  {market:"美股",cat:"企业公告",title:"康宁下调季度指引，玻璃需求承压",body:"终端需求疲软，盖板出货放缓。"},
  {market:"宏观",cat:"宏观数据",title:"美联储维持利率不变，表态偏鸽",body:"点阵图暗示年内降息空间。"},
  {market:"A股",cat:"政策动态",title:"国内算力补贴政策出台，扶持智算中心",body:"对智算中心建设给予财政补贴。"},
  {market:"A股",cat:"企业公告",title:"东山精密获 AI 服务器大单",body:"斩获头部客户精密制造订单。"},
  {market:"美股",cat:"财经快讯",title:"特斯拉销量略不及预期，供应链承压",body:"交付节奏放缓，降价压力上升。"},
  {market:"日韩",cat:"行业调研",title:"东京电子对华设备限制加码，国产替代提速",body:"半导体设备国产化逻辑强化。"},
  {market:"美股",cat:"投研报告",title:"某科技龙头业绩平稳符合预期",body:"营收与指引基本符合市场共识。"},
];
EVENTS.forEach(e=>{const s=classify(e.title+" "+e.body);e.senti=s.tier;e.conf=s.conf;e.affected=mapAffected(e.title,e.body);});
function searchEvents(q){q=(q||"").trim().toLowerCase();if(!q)return null;const hit=new Set();
  EVENTS.forEach((e,i)=>{const text=(e.title+" "+e.body+" "+e.market).toLowerCase();if(text.includes(q))hit.add(i);e.affected.forEach(a=>{if((a.name+a.code).toLowerCase().includes(q)||(a.code||"").toLowerCase().includes(q))hit.add(i);});});
  if(hit.size===0){const parents=[];for(const k in KG){const node=KG[k];const selfQ=(k.toLowerCase().includes(q))||node.alias.some(a=>a.toLowerCase().includes(q));const inAffects=node.affects.some(([code,name])=>(name.toLowerCase().includes(q))||(code.toLowerCase().includes(q)));if(selfQ||inAffects)parents.push(k);}
    parents.forEach(p=>EVENTS.forEach((e,i)=>{if((e.title+" "+e.body).toLowerCase().includes(p.toLowerCase()))hit.add(i);}));
    if(hit.size===0){const stocks=new Set();parents.forEach(p=>KG[p].affects.forEach(([code])=>stocks.add(code)));EVENTS.forEach((e,i)=>e.affected.forEach(a=>{if(stocks.has(a.code))hit.add(i);}));}}
  return [...hit];}
const POOL=["英伟达","三星","海力士","AMD","美光","英特尔","康宁","中际旭创","东山精密","寒武纪","兆易创新","长江存储","长鑫存储"];
let allok=true;
console.log("=== 优先池 13 只 ===");
for(const p of POOL){const r=searchEvents(p);const n=r?r.length:0;if(n===0)allok=false;console.log(`${p.padEnd(6)} -> ${n} 条 ${n===0?"❌扑空":""}`);}
console.log("=== 持仓 / 代码 / 别名 ===");
for(const q of ["300308","688256","603986","NVDA","新易盛","澜起科技","北京君正","京东方A"]){const r=searchEvents(q);console.log(`${q.padEnd(8)} -> ${r?r.length:0} 条`);}
console.log(allok?"\n✅ 全部优先池股票均有命中":"\n⚠️ 仍有扑空");
