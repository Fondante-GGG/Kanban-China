// Mock API browser verification. Does not write to the application's database.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = process.env.UI_BASE_URL || 'http://127.0.0.1:3015';
const axePath = process.env.AXE_MODULE || require.resolve('axe-core/axe.min.js');
const names = {name_ru:'Товар',name_ky:'Товар',name_zh:'商品'};
const warehouse = id => ({id,name_ru:id===1?'Бишкек':'Ош',name_ky:id===1?'Бишкек':'Ош',name_zh:id===1?'比什凯克':'奥什',locations:[{id:id*10,code:id===1?'A-01':'B-01'}]});
const actorPermissions = {
 sender:['warehouse.inventory.read','warehouse.transfer.read','warehouse.transfer.manage','warehouse.transfer.post'],
 reviewer:['warehouse.inventory.read','warehouse.transfer.read','warehouse.transfer.approve'],
 receiver:['warehouse.inventory.read','warehouse.transfer.read','warehouse.transfer.receive'],
};
const labels = {
 ru:{warehouse:'Склад',title:'Перемещения',open:'Открыть',close:'Закрыть детали'},
 ky:{warehouse:'Кампа',title:'Которуулар',open:'Ачуу',close:'Чоо-жайды жабуу'},
 'zh-Hans':{warehouse:'仓库',title:'调拨',open:'打开',close:'关闭详情'},
 'zh-Hant':{warehouse:'倉庫',title:'調撥',open:'開啟',close:'關閉詳情'},
};
const freshTransfer = () => ({id:1,transfer_no:'TR-TEST',source_warehouse_id:1,destination_warehouse_id:2,
 source_name_ru:'Бишкек',source_name_ky:'Бишкек',source_name_zh:'比什凯克',destination_name_ru:'Ош',destination_name_ky:'Ош',destination_name_zh:'奥什',
 status:'draft',created_at:'2026-10-31T08:00:00Z',created_by_name:'Sender',approved_at:null,approved_by_name:null,
 dispatched_at:null,dispatched_by_name:null,received_at:null,received_by_name:null,comment:'Тест',review_comment:'',history:[],in_transit_qty:'0',
 items:[{id:1,sku_id:1,sku_code:'SKU-1',...names,qty:3,source_location_id:10,source_location_code:'A-01',destination_location_id:20,destination_location_code:'B-01',batch_no:'BATCH-1',expiry_date:'2027-10-31',in_transit_qty:'0'}]});
function allowed(actor,status) {
 if(actor==='sender')return status==='draft'?['edit','submit','cancel']:status==='pending_approval'?['cancel']:status==='approved'?['dispatch','cancel']:[];
 if(actor==='reviewer'&&status==='pending_approval')return ['review'];
 if(actor==='receiver'&&status==='in_transit')return ['receive'];
 return [];
}
function state(initial='draft') {
 const transfer=freshTransfer();transfer.status=initial;
 if(initial==='in_transit'){transfer.in_transit_qty='3';transfer.items[0].in_transit_qty='3';transfer.dispatched_at='2026-10-31T09:00:00Z';transfer.approved_at='2026-10-31T08:30:00Z';}
 return {transfer,exists:true,calls:[],revoked:false,sourceQty:initial==='in_transit'?7:10,destQty:0};
}
async function context(browser,shared,actor,lang='ru',dark=false,width=360) {
 const ctx=await browser.newContext({viewport:{width,height:960}});
 await ctx.addInitScript(({actor,lang,dark})=>{localStorage.setItem('kanban_token',actor);localStorage.setItem('kanban_lang',lang);localStorage.setItem('kanban_theme',dark?'dark':'light');},{actor,lang,dark});
 const page=await ctx.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const own=actor==='receiver'?2:1,permissions=actorPermissions[actor];
 await page.route('**/api/**',async route=>{
  const url=new URL(route.request().url());const path=url.pathname.replace(/^\/api\//,'');const verb=route.request().method();let data={};
  if(path==='auth/me')data={id:actor==='sender'?2:actor==='reviewer'?3:4,email:actor+'@test',full_name:actor,role:actor==='reviewer'?'general_director':'employee',department_id:1,interface_language:lang,assigned_board_id:null,system_permissions:permissions};
  else if(path==='boards')data={boards:[]};
  else if(path==='notifications')data={notifications:[]};
  else if(path.startsWith('warehouse/')){
   if(shared.revoked || (path==='warehouse/transfers/catalog'&&shared.catalogForbidden))return route.fulfill({status:403,contentType:'application/json',body:JSON.stringify({code:'permission_denied',error:'Denied'})});
   if(path==='warehouse/catalog')data={permissions,warehouses:[warehouse(own)],skus:[{id:1,sku_code:'SKU-1',...names}],purchase_orders:[]};
   else if(path==='warehouse/transfers/catalog')data={permissions,sources:[warehouse(own)],destinations:[warehouse(1),warehouse(2)],skus:[{id:1,sku_code:'SKU-1',...names}],stock:[{warehouse_id:own,sku_id:1,location_id:own*10,location_code:own===1?'A-01':'B-01',qty:String(own===1?shared.sourceQty:shared.destQty),unbatched_qty:'0',batches:own===1?[{batch_no:'BATCH-1',expiry_date:'2027-10-31',qty:String(shared.sourceQty)}]:[]}]};
   else if(path==='warehouse/transfers'&&verb==='GET'){
    if(url.searchParams.has('id')&&shared.failNextDetail){shared.failNextDetail=false;return route.fulfill({status:500,contentType:'application/json',body:JSON.stringify({error:'Temporary failure'})});}
    if(url.searchParams.has('id')&&shared.detailForbidden)return route.fulfill({status:403,contentType:'application/json',body:JSON.stringify({code:'permission_denied',error:'Denied'})});
    const show=shared.exists&&(!shared.outsidePage||url.searchParams.has('id'));
    data={items:show?[{...shared.transfer,allowed_actions:allowed(actor,shared.transfer.status)}]:[],count:show?1:0};
   }
   else if(path==='warehouse/movements'&&shared.movements)data={items:[{id:5,warehouse_id:own,warehouse_name_ru:'Бишкек',warehouse_name_ky:'Бишкек',warehouse_name_zh:'比什凯克',sku_id:1,sku_code:'SKU-1',...names,location_id:10,location_code:'A-01',qty_delta:'-3',movement_type:'transfer_out',source_type:'stock_transfer',source_id:1,source_no:shared.transfer.transfer_no,reason:'',posted_at:'2026-10-31T09:00:00Z'}],count:1};
   else if(path.startsWith('warehouse/transfers')&&(verb==='POST'||verb==='PATCH')){
    const body=route.request().postDataJSON()||{};shared.calls.push({actor,path,verb,body});
    const action=path.split('/').at(-1);const t=shared.transfer;
    if(path==='warehouse/transfers'){shared.exists=true;t.transfer_no=body.transfer_no;t.comment=body.comment||'';}
    else if(verb==='PATCH'){t.comment=body.comment||'';}
    else if(action==='submit')t.status='pending_approval';
    else if(action==='review'){t.review_comment=body.comment||'';t.status=body.decision==='approve'?'approved':body.decision==='return'?'draft':'rejected';}
    else if(action==='dispatch'){t.status='in_transit';t.dispatched_at='2026-10-31T09:00:00Z';t.in_transit_qty='3';t.items[0].in_transit_qty='3';shared.sourceQty=7;}
    else if(action==='receive'){t.status='received';t.received_at='2026-10-31T10:00:00Z';t.in_transit_qty='0';t.items[0].in_transit_qty='0';shared.destQty=3;}
    else if(action==='cancel')t.status='cancelled';
    data={id:1,status:t.status};
   }else data={items:[],count:0};
  }
  const body=JSON.stringify(data);
  if(path==='warehouse/transfers'&&verb==='GET'&&url.searchParams.has('id')&&shared.detailGate){const gate=shared.detailGate;shared.detailGate=null;await gate;}
  if(path==='warehouse/transfers/catalog'&&shared.catalogGate){const gate=shared.catalogGate;shared.catalogGate=null;await gate;}
  await route.fulfill({status:200,contentType:'application/json',body});
 });
 await page.goto(base);await page.getByRole('button',{name:labels[lang].warehouse,exact:true}).click();
 const root=page.locator('main section').first();
 await root.getByRole('button',{name:labels[lang].title,exact:true}).click();
 await root.getByRole('button',{name:labels[lang].open,exact:true}).first().waitFor();
 return {ctx,page,root,errors};
}
async function axeCheck(page) {
 await page.addScriptTag({path:axePath});
 return page.evaluate(async()=>{const result=await axe.run(document.querySelector('main section'),{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return result.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}));});
}
if (require.main === module) (async()=>{
 const browser=await chromium.launch({headless:true});fs.mkdirSync('/tmp/yrys-transfer-check',{recursive:true});
 const results=[];
 try {
  for(const lang of Object.keys(labels))for(const dark of [false,true])for(const width of [360,1440]){
   const {ctx,page,root,errors}=await context(browser,state('in_transit'),'receiver',lang,dark,width);
   await root.getByRole('button',{name:labels[lang].open,exact:true}).click();
   const violations=await axeCheck(page);
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
   results.push({lang,dark,width,errors,overflow,violations});console.log(JSON.stringify(results.at(-1)));
   await page.screenshot({path:`/tmp/yrys-transfer-check/${lang}-${dark?'dark':'light'}-${width}.png`,fullPage:true});
   await ctx.close();
  }
  fs.writeFileSync('/tmp/yrys-transfer-check/results.json',JSON.stringify(results,null,2));
  assert(results.every(x=>!x.errors.length&&!x.overflow&&!x.violations.length),'Matrix failed');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
module.exports={context,state,axeCheck,labels};
