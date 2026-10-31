// Mock API only. No warehouse data or photos are written to the application DB.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const base=process.env.UI_BASE_URL||'http://127.0.0.1:3015';
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAABAAAAAMCAIAAADkharWAAAAF0lEQVR4nGNcEBDAQApgIkn1qIYRpAEA+soBWDh3OYsAAAAASUVORK5CYII=','base64');
const names={name_ru:'Товар',name_ky:'Товар',name_zh:'商品'};
const wh={id:1,name_ru:'Бишкек',name_ky:'Бишкек',name_zh:'比什凯克',locations:[{id:10,code:'A-01'}]};
const actorPermissions={operator:['warehouse.inventory.read','warehouse.writeoff.read','warehouse.writeoff.manage','warehouse.writeoff.post'],reviewer:['warehouse.inventory.read','warehouse.writeoff.read','warehouse.writeoff.approve']};
const labels={ru:{warehouse:'Склад',title:'Списания',open:'Открыть',photo:'Показать фотографию'},ky:{warehouse:'Кампа',title:'Эсептен чыгаруу',open:'Ачуу',photo:'Сүрөттү көрсөтүү'},'zh-Hans':{warehouse:'仓库',title:'报损',open:'打开',photo:'显示照片'},'zh-Hant':{warehouse:'倉庫',title:'報損',open:'開啟',photo:'顯示照片'}};
const photo=(id=1)=>({id,file_name:`evidence-${id}.png`,content_type:'image/png',size:png.length,download_url:`/api/warehouse/writeoffs/1/photos/${id}/download`});
function state(status='draft',photos=[]){return{doc:{id:1,writeoff_no:'WO-TEST',warehouse_id:1,warehouse_name_ru:wh.name_ru,warehouse_name_ky:wh.name_ky,warehouse_name_zh:wh.name_zh,status,reason:'Истёк срок годности',review_comment:'',created_at:'2026-10-31T08:00:00Z',created_by_name:'Operator',approved_at:null,approved_by_name:null,posted_at:null,posted_by_name:null,items:[{id:1,sku_id:1,sku_code:'SKU-1',...names,qty:'1.250',location_id:10,location_code:'A-01',batch_no:'BATCH-1',expiry_date:'2026-10-30'}],photos,history:[]},calls:[],downloads:[],revoked:false,stock:'10.500',nextPhoto:2};}
function allowed(actor,status){if(actor==='operator')return status==='draft'?['edit','upload_photo','delete_photo','submit','cancel']:status==='pending_approval'?['cancel']:status==='approved'?['post','cancel']:[];return status==='pending_approval'?['review']:[];}
async function context(browser,shared,actor='operator',lang='ru',dark=false,width=360){
 const ctx=await browser.newContext({viewport:{width,height:960}});
 await ctx.addInitScript(({actor,lang,dark})=>{localStorage.setItem('kanban_token',actor);localStorage.setItem('kanban_lang',lang);localStorage.setItem('kanban_theme',dark?'dark':'light');const create=URL.createObjectURL.bind(URL),revoke=URL.revokeObjectURL.bind(URL);window.__photoUrls={live:new Set(),created:0,revoked:0};URL.createObjectURL=blob=>{const url=create(blob);window.__photoUrls.live.add(url);window.__photoUrls.created++;return url;};URL.revokeObjectURL=url=>{window.__photoUrls.live.delete(url);window.__photoUrls.revoked++;return revoke(url);};},{actor,lang,dark});
 const page=await ctx.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const permissions=actorPermissions[actor];
 await page.route('**/api/**',async route=>{
  const request=route.request(),url=new URL(request.url()),path=url.pathname.replace(/^\/api\//,''),verb=request.method();let data={};
  if(path==='auth/me')data={id:actor==='operator'?2:3,email:actor+'@test',full_name:actor,role:actor==='reviewer'?'general_director':'employee',department_id:1,interface_language:lang,assigned_board_id:null,system_permissions:permissions};
  else if(path==='boards')data={boards:[]};else if(path==='notifications')data={notifications:[]};
  else if(path.startsWith('warehouse/')){
   if(shared.revoked)return route.fulfill({status:403,contentType:'application/json',body:JSON.stringify({error:'Denied',code:'permission_denied'})});
   if(/warehouse\/writeoffs\/1\/photos\/\d+\/download$/.test(path)){
    shared.downloads.push({path,authorization:request.headers().authorization});
    if(shared.photoDenied)return route.fulfill({status:403,contentType:'application/json',body:JSON.stringify({error:'Denied',code:'permission_denied'})});
    if(shared.photoGate){const gate=shared.photoGate;shared.photoGate=null;await gate;}
    return route.fulfill({status:200,contentType:'image/png',body:png}).catch(()=>{});
   }
   if(path==='warehouse/catalog')data={permissions,warehouses:[wh],skus:[{id:1,sku_code:'SKU-1',...names}],purchase_orders:[]};
   else if(path==='warehouse/writeoffs/catalog')data={permissions,warehouses:[wh],skus:[{id:1,sku_code:'SKU-1',...names}],stock:[{warehouse_id:1,sku_id:1,location_id:10,location_code:'A-01',qty:shared.stock,unbatched_qty:'0',batches:[{batch_no:'BATCH-1',expiry_date:'2026-10-30',qty:shared.stock}]}]};
   else if(path==='warehouse/writeoffs'&&verb==='GET'){
    if(url.searchParams.has('id')&&(shared.failNextDetail||shared.detailFailure)){shared.failNextDetail=false;return route.fulfill({status:500,contentType:'application/json',body:JSON.stringify({error:'Temporary failure'})});}
    const show=!shared.outsidePage||url.searchParams.has('id');data={items:show?[{...shared.doc,allowed_actions:allowed(actor,shared.doc.status)}]:[],count:show?1:0};
   }else if(path==='warehouse/movements'&&shared.movements)data={items:[{id:5,warehouse_id:1,warehouse_name_ru:wh.name_ru,warehouse_name_ky:wh.name_ky,warehouse_name_zh:wh.name_zh,sku_id:1,sku_code:'SKU-1',...names,location_id:10,location_code:'A-01',qty_delta:'-1.25',movement_type:'issue',source_type:'stock_writeoff',source_id:1,source_no:shared.doc.writeoff_no,reason:shared.doc.reason,posted_at:'2026-10-31T09:00:00Z'}],count:1};
   else if(path.startsWith('warehouse/writeoffs')&&['POST','PATCH','DELETE'].includes(verb)){
    const isUpload=/\/photos$/.test(path)&&verb==='POST';
    const body=isUpload?null:request.postDataJSON()||{};shared.calls.push({actor,path,verb,body,headers:request.headers(),multipartContainsPng:isUpload?request.postDataBuffer().includes(png):undefined});
    if(isUpload&&shared.failNextUpload){shared.failNextUpload=false;return route.fulfill({status:400,contentType:'application/json',body:JSON.stringify({error:'Invalid image',code:'invalid_photo'})});}
    const doc=shared.doc,action=path.split('/').at(-1);
    if(path==='warehouse/writeoffs'){doc.writeoff_no=body.writeoff_no;doc.reason=body.reason;doc.items[0].qty=body.items[0].qty;doc.photos=[];doc.status='draft';}
    else if(verb==='PATCH'){doc.reason=body.reason;doc.items[0].qty=body.items[0].qty;}
    else if(isUpload){const p=photo(shared.nextPhoto++);doc.photos.push(p);data=p;}
    else if(verb==='DELETE'){doc.photos=doc.photos.filter(p=>p.id!==Number(action));}
    else if(action==='submit'){assert(doc.photos.length>0);doc.status='pending_approval';}
    else if(action==='review'){doc.review_comment=body.comment||'';doc.status=body.decision==='approve'?'approved':body.decision==='return'?'draft':'rejected';}
    else if(action==='post'){assert.equal(doc.status,'approved');doc.status='posted';doc.posted_at='2026-10-31T10:00:00Z';shared.stock=String(Number(shared.stock)-Number(doc.items[0].qty));}
    else if(action==='cancel')doc.status='cancelled';
    if(!isUpload)data={id:1,status:doc.status};
   }else data={items:[],count:0};
  }
  const body=JSON.stringify(data);
  if(path==='warehouse/writeoffs'&&verb==='GET'&&url.searchParams.has('id')&&shared.detailGate){const gate=shared.detailGate;shared.detailGate=null;await gate;}
  await route.fulfill({status:200,contentType:'application/json',body});
 });
 await page.goto(base);await page.getByRole('button',{name:labels[lang].warehouse,exact:true}).click();
 const root=page.locator('main section').first();await root.getByRole('button',{name:labels[lang].title,exact:true}).click();
 await root.getByRole('button',{name:labels[lang].open,exact:true}).first().waitFor();return{ctx,page,root,errors};
}
async function axeCheck(page){await page.addScriptTag({path:process.env.AXE_MODULE||require.resolve('axe-core/axe.min.js')});return page.evaluate(async()=>{const r=await axe.run(document.querySelector('main section'),{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return r.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}));});}
if(require.main===module)(async()=>{
 const browser=await chromium.launch({headless:true});const results=[];fs.mkdirSync('/tmp/yrys-writeoff-check',{recursive:true});
 try{for(const lang of Object.keys(labels))for(const dark of[false,true])for(const width of[360,1440]){
  const shared=state('pending_approval',[photo()]);const {ctx,page,root,errors}=await context(browser,shared,'reviewer',lang,dark,width);
  await root.getByRole('button',{name:labels[lang].open,exact:true}).click();
  await root.getByRole('button',{name:`${labels[lang].photo} 1`,exact:true}).click();
  await page.waitForFunction(()=>[...document.querySelectorAll('main section img')].some(img=>img.complete&&img.naturalWidth>0&&img.src.startsWith('blob:')));
  const violations=await axeCheck(page),overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
  assert(shared.downloads.every(d=>d.authorization==='Bearer reviewer'));
  const row={lang,dark,width,errors,overflow,violations,authenticatedPhotos:shared.downloads.length};results.push(row);console.log(JSON.stringify(row));
  await page.screenshot({path:`/tmp/yrys-writeoff-check/${lang}-${dark?'dark':'light'}-${width}.png`,fullPage:true});await ctx.close();
 }fs.writeFileSync('/tmp/yrys-writeoff-check/results.json',JSON.stringify(results,null,2));assert(results.every(r=>!r.errors.length&&!r.overflow&&!r.violations.length));}finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
module.exports={context,state,photo,png,axeCheck};
