// Mock API checks; these scenarios never change the working database.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs');
const base=process.env.UI_BASE_URL||'http://127.0.0.1:3015';
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAABAAAAAMCAIAAADkharWAAAAF0lEQVR4nGNcEBDAQApgIkn1qIYRpAEA+soBWDh3OYsAAAAASUVORK5CYII=','base64');
const names={name_ru:'Товар',name_ky:'Товар',name_zh:'商品'},wh={id:1,name_ru:'Бишкек',name_ky:'Бишкек',name_zh:'比什凯克',locations:[{id:10,code:'A-01'}]};
const permissions={operator:['warehouse.inventory.read','warehouse.return.read','warehouse.return.manage','warehouse.return.post'],reviewer:['warehouse.inventory.read','warehouse.return.read','warehouse.return.approve'],finance:['finance.payable.read']};
const labels={ru:{warehouse:'Склад',title:'Возвраты поставщикам',open:'Открыть',photo:'Показать фотографию',finance:'Расходы',financeTitle:'Возвраты: финансовое рассмотрение'},ky:{warehouse:'Кампа',title:'Жеткирүүчүгө кайтаруулар',open:'Ачуу',photo:'Сүрөттү көрсөтүү',finance:'Чыгымдар',financeTitle:'Кайтаруулар: финансылык кароо'},'zh-Hans':{warehouse:'仓库',title:'供应商退货',open:'打开',photo:'显示照片',finance:'费用',financeTitle:'退货：财务审核'},'zh-Hant':{warehouse:'倉庫',title:'供應商退貨',open:'開啟',photo:'顯示照片',finance:'費用',financeTitle:'退貨：財務審核'}};
const photo=(finance=false)=>({id:1,file_name:'return.png',content_type:'image/png',size:png.length,download_url:finance?'/api/finance/supplier-returns/10/photos/1/download':'/api/warehouse/returns/1/photos/1/download'});
function state(status='draft',photos=[],reasonType='damage'){
 const expiry=new Date(Date.now()+365*86400000).toISOString().slice(0,10);
 return{doc:{id:1,return_no:'RET-1',receipt_id:1,receipt_no:'REC-1',warehouse_id:1,warehouse_name_ru:wh.name_ru,warehouse_name_ky:wh.name_ky,warehouse_name_zh:wh.name_zh,supplier_id:1,supplier_name:'Поставщик',reason_type:reasonType,reason:'Порча товара',review_comment:'',status,created_at:'2026-10-31T08:00:00Z',created_by_name:'Operator',approved_at:null,approved_by_name:null,posted_at:status==='posted'?'2026-10-31T09:00:00Z':null,posted_by_name:null,finance_review_status:status==='posted'?'pending':null,photos_required:reasonType!=='other',items:[{id:1,receipt_item_id:1,sku_id:1,sku_code:'SKU-1',...names,qty:'2',location_id:10,location_code:'A-01',batch_no:'BATCH-1',expiry_date:expiry}],photos,history:[]},calls:[],downloads:[],revoked:false,financeDenied:false,stock:5,returned:status==='posted'?2:0,paid:'50.00',debt:'100.00'};
}
const allowed=(actor,status)=>actor==='operator'?(status==='draft'?['edit','upload_photo','delete_photo','submit','cancel']:status==='pending_approval'?['cancel']:status==='approved'?['post','cancel']:[]):actor==='reviewer'&&status==='pending_approval'?['review']:[];
function financeItem(s){const d=s.doc;return{id:10,return_id:1,return_no:d.return_no,receipt_id:1,receipt_no:'REC-1',supplier_id:1,supplier_name:d.supplier_name,warehouse_id:1,status:'pending',created_at:'2026-10-31T09:00:00Z',posted_at:d.posted_at||'2026-10-31T09:00:00Z',source_currency:'CNY',valuation_currency:null,valuation_status:'currency_unresolved',stock_valuation:'10.00',items:d.items.map(x=>({...x,unit_cost:'5.00'})),photos:d.photos.map(()=>photo(true))};}
async function context(browser,s,actor='operator',lang='ru',dark=false,width=360,setup,skipSection=false){
 const ctx=await browser.newContext({viewport:{width,height:960}});
 await ctx.addInitScript(({actor,lang,dark})=>{localStorage.setItem('kanban_token',actor);localStorage.setItem('kanban_lang',lang);localStorage.setItem('kanban_theme',dark?'dark':'light');const create=URL.createObjectURL.bind(URL),revoke=URL.revokeObjectURL.bind(URL);window.__urls=new Set();URL.createObjectURL=b=>{const u=create(b);window.__urls.add(u);return u};URL.revokeObjectURL=u=>{window.__urls.delete(u);return revoke(u)};},{actor,lang,dark});
 const page=await ctx.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/**',async route=>{
  const request=route.request(),url=new URL(request.url()),path=url.pathname.replace(/^\/api\//,''),verb=request.method();let data={};
  if(path==='auth/me')data={id:actor==='operator'?2:actor==='reviewer'?3:4,email:actor+'@test',full_name:actor,role:actor==='reviewer'?'general_director':actor==='finance'?'accountant':'employee',department_id:1,interface_language:lang,assigned_board_id:null,system_permissions:permissions[actor]};
  else if(path==='boards')data={boards:[]};
  else if(path==='notifications')data={notifications:s.doc.status==='posted'?[{id:99,title:'Supplier return',message:'Check return',entity_type:'supplier_return',entity_id:1,is_read:false,created_at:'2026-10-31T09:00:00Z'}]:[]};
  else if(path==='expenses')data={expenses:[]};
  else if(path==='expenses/analytics')data={summary:{total:'0',count:'0',personal:'0',pending:'0'}};
  else if(path.startsWith('warehouse/')||path.startsWith('finance/supplier-returns')){
   if(s.revoked||(s.financeDenied&&path.startsWith('finance/')))return route.fulfill({status:403,contentType:'application/json',body:JSON.stringify({error:'Denied',code:'permission_denied'})});
   if(path.endsWith('/photos/1/download')){s.downloads.push({actor,path,authorization:request.headers().authorization});if(s.photoGate){const gate=s.photoGate;s.photoGate=null;await gate;}return route.fulfill({status:200,contentType:'image/png',body:png}).catch(()=>{});}
   if(path==='warehouse/catalog')data={warehouses:[wh],permissions:permissions[actor],skus:[],purchase_orders:[]};
   else if(path==='warehouse/returns/catalog'){
    const r={id:1,receipt_no:'REC-1',warehouse_id:1,supplier_id:1,supplier_name:'Поставщик',items:[{receipt_item_id:1,sku_id:1,sku_code:'SKU-1',...names,location_id:10,location_code:'A-01',batch_no:'BATCH-1',expiry_date:s.doc.items[0].expiry_date,received_qty:5,returned_qty:s.returned,returnable_qty:5-s.returned}]};
    data={warehouses:[wh],permissions:permissions[actor],receipts:[r],receipt_count:1,limit:20,offset:0};
   }else if(path==='warehouse/returns'&&verb==='GET'){
    if(url.searchParams.has('id')&&s.detailFailure)return route.fulfill({status:500,contentType:'application/json',body:JSON.stringify({error:'Temporary failure'})});
    const show=!s.outsidePage||url.searchParams.has('id');data={items:show?[{...s.doc,allowed_actions:allowed(actor,s.doc.status)}]:[],count:show?1:0};
   }else if(path==='warehouse/movements'&&s.movements)data={items:[{id:5,warehouse_id:1,warehouse_name_ru:wh.name_ru,warehouse_name_ky:wh.name_ky,warehouse_name_zh:wh.name_zh,sku_id:1,sku_code:'SKU-1',...names,location_id:10,location_code:'A-01',qty_delta:'-2',movement_type:'issue',source_type:'supplier_return',source_id:1,source_no:s.doc.return_no,reason:s.doc.reason,posted_at:'2026-10-31T09:00:00Z'}],count:1};
   else if(path==='finance/supplier-returns')data={items:s.doc.status==='posted'?[financeItem(s)]:[],count:s.doc.status==='posted'?1:0};
   else if(path.startsWith('warehouse/returns')&&['POST','PATCH','DELETE'].includes(verb)){
    const upload=path.endsWith('/photos')&&verb==='POST',body=upload?null:request.postDataJSON()||{};s.calls.push({actor,path,verb,body,png:upload?request.postDataBuffer().includes(png):undefined});const d=s.doc,action=path.split('/').at(-1);
    if(path==='warehouse/returns'){d.return_no=body.return_no;d.reason_type=body.reason_type;d.reason=body.reason;d.items[0].qty=String(body.items[0].qty);d.photos_required=body.reason_type!=='other';d.photos=[];d.status='draft';}
    else if(verb==='PATCH'){d.reason=body.reason;d.reason_type=body.reason_type;d.items[0].qty=String(body.items[0].qty);}
    else if(upload){d.photos=[photo()];data=photo();}
    else if(verb==='DELETE')d.photos=[];
    else if(action==='submit'){assert(!d.photos_required||d.photos.length);d.status='pending_approval';}
    else if(action==='review'){d.review_comment=body.comment||'';d.status=body.decision==='approve'?'approved':body.decision==='return'?'draft':'rejected';}
    else if(action==='post'){if(s.conflictPost){d.status='posted';return route.fulfill({status:409,contentType:'application/json',body:JSON.stringify({error:'Already posted',code:'conflict'})});}assert.equal(d.status,'approved');d.status='posted';d.posted_at='2026-10-31T09:00:00Z';d.finance_review_status='pending';s.stock-=Number(d.items[0].qty);s.returned+=Number(d.items[0].qty);}
    else if(action==='cancel')d.status='cancelled';if(!upload)data={id:1,status:d.status};
   }else data={items:[],count:0};
  }
  const body=JSON.stringify(data);if(path==='warehouse/returns'&&url.searchParams.has('id')&&s.detailGate){const gate=s.detailGate;s.detailGate=null;await gate;}
  await route.fulfill({status:200,contentType:'application/json',body});
 });
 if(setup)await setup({ctx,page});
 await page.goto(base);
 if(skipSection)return{ctx,page,errors};
 if(actor==='finance'){await page.getByRole('button',{name:labels[lang].finance,exact:true}).click();await page.getByRole('heading',{name:labels[lang].financeTitle,exact:true}).waitFor();}
 else{await page.getByRole('button',{name:labels[lang].warehouse,exact:true}).click();await page.locator('main section').first().getByRole('button',{name:labels[lang].title,exact:true}).click();await page.getByRole('button',{name:labels[lang].open,exact:true}).first().waitFor();}
 return{ctx,page,root:actor==='finance'?page.getByRole('region',{name:labels[lang].financeTitle,exact:true}):page.locator('main section').first(),errors};
}
async function axeCheck(page,selector='main section'){await page.addScriptTag({path:process.env.AXE_MODULE||require.resolve('axe-core/axe.min.js')});return page.evaluate(async(selector)=>{const r=await axe.run(document.querySelector(selector),{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return r.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}));},selector);}
if(require.main===module)(async()=>{const browser=await chromium.launch({headless:true}),results=[];fs.mkdirSync('/tmp/yrys-returns-check',{recursive:true});try{for(const actor of['reviewer','finance'])for(const lang of Object.keys(labels))for(const dark of[false,true])for(const width of[360,1440]){
 const s=state(actor==='finance'?'posted':'pending_approval',[photo()]);const {ctx,page,root,errors}=await context(browser,s,actor,lang,dark,width);if(actor!=='finance')await root.getByRole('button',{name:labels[lang].open,exact:true}).click();await root.getByRole('button',{name:`${labels[lang].photo} 1`,exact:true}).click();await page.waitForFunction(()=>[...document.querySelectorAll('main img')].some(i=>i.complete&&i.naturalWidth>0&&i.src.startsWith('blob:')));
 const violations=await axeCheck(page,actor==='finance'?'section[aria-labelledby="supplier-return-finance-heading"]':'main section'),overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);assert(s.downloads.every(d=>d.authorization===`Bearer ${actor}`));if(actor==='finance')assert(s.downloads.every(d=>d.path.startsWith('finance/')));const result={actor,lang,dark,width,errors,overflow,violations};results.push(result);console.log(JSON.stringify(result));await page.screenshot({path:`/tmp/yrys-returns-check/${actor}-${lang}-${dark?'dark':'light'}-${width}.png`,fullPage:true});await ctx.close();
 }fs.writeFileSync('/tmp/yrys-returns-check/results.json',JSON.stringify(results,null,2));assert(results.every(r=>!r.errors.length&&!r.overflow&&!r.violations.length));}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
module.exports={context,state,photo,png,axeCheck};
