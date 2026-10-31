const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('fs');
const assert = require('node:assert/strict');
const perms = ['warehouse.inventory.read','warehouse.receipt.read','warehouse.receipt.manage','warehouse.receipt.post','warehouse.count.read','warehouse.count.manage','warehouse.count.approve'];
const names = {name_ru:'Товар',name_ky:'Товар',name_zh:'商品'};
const whnames = {warehouse_name_ru:'Бишкек',warehouse_name_ky:'Бишкек',warehouse_name_zh:'比什凯克'};
const fixture = {
 catalog:{permissions:perms, warehouses:[{id:1,name_ru:'Бишкек',name_ky:'Бишкек',name_zh:'比什凯克',locations:[{id:1,code:'A-01'}]}],skus:[{id:1,sku_code:'SKU-1',...names}],purchase_orders:[{id:1,po_no:'PO-1',currency:'KGS',items:[{id:1,sku_id:1,sku_code:'SKU-1',...names,ordered_qty:10,received_qty:0}]}]},
 inventory:{count:1,items:[{id:1,warehouse_id:1,...whnames,sku_id:1,sku_code:'SKU-1',...names,location_id:null,location_code:null,qty:'10.000',batches:[]}]},
 movements:{count:1,items:[{id:1,warehouse_id:1,...whnames,sku_id:1,sku_code:'SKU-1',...names,location_id:null,location_code:null,qty_delta:'10.000',movement_type:'receipt',source_type:'purchase_receipt',source_id:1,reason:'',posted_at:'2026-10-31T10:00:00Z'}]},
 receipts:{count:1,items:[{id:1,receipt_no:'REC-1',warehouse_id:1,...whnames,purchase_order_id:1,po_no:'PO-1',status:'draft',comment:'',received_at:'2026-10-31T10:00:00Z',allowed_actions:['post'],items:[{id:1,po_item_id:1,sku_id:1,sku_code:'SKU-1',...names,qty:10,location_id:null,location_code:null,batch_no:'',expiry_date:null,discrepancy_reason:''}]}]},
 counts:{count:1,items:[{id:1,count_no:'CNT-1',warehouse_id:1,...whnames,status:'counted',allowed_actions:['approve'],created_at:'2026-10-31T10:00:00Z',items:[{id:1,sku_id:1,sku_code:'SKU-1',...names,system_qty:'10.000',actual_qty:'9.000',reason:'Уточнение'}]}]},
 expiry:{as_of:'2026-10-31',days:30,batches:[],certificates:[]},
};
const ui = {
 ru:['Склад','Остатки','Движения','Приёмки','Инвентаризации','Сроки годности'],
 ky:['Кампа','Калдыктар','Кыймылдар','Кабыл алуулар','Инвентаризациялар','Жарактуулук мөөнөтү'],
 'zh-Hans':['仓库','库存','库存流水','收货单','盘点单','有效期'],
 'zh-Hant':['倉庫','庫存','庫存明細','收貨單','盤點單','有效期限'],
};
(async()=>{
 const browser = await chromium.launch({headless:true});
 const results=[];
 fs.mkdirSync('/tmp/yrys-ui-check', {recursive:true});
 try {
  for (const lang of Object.keys(ui)) for (const dark of [false,true]) for (const width of [360,1440]) {
   const ctx=await browser.newContext({viewport:{width,height:900}});
   await ctx.addInitScript(({lang,dark})=>{localStorage.setItem('kanban_token','browser-fixture');localStorage.setItem('kanban_lang',lang);localStorage.setItem('kanban_theme',dark?'dark':'light');},{lang,dark});
   const page=await ctx.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.route('**/api/**',async route=>{
    const path=new URL(route.request().url()).pathname.replace(/^\/api\//,'');let data={};
    if(path==='auth/me')data={id:2,email:'wms@test',full_name:'Warehouse Tester',role:'employee',department_id:1,interface_language:lang,assigned_board_id:null,system_permissions:perms};
    else if(path==='boards')data={boards:[]};
    else if(path==='notifications')data={notifications:[]};
    else if(path==='warehouse/alerts/expiry')data=fixture.expiry;
    else if(path.startsWith('warehouse/'))data=fixture[path.split('/')[1]]||{};
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(data)});
   });
   await page.goto(process.env.UI_BASE_URL || 'http://127.0.0.1:3015');
   await page.getByRole('button',{name:ui[lang][0],exact:true}).click();
   await page.getByRole('heading',{level:1,name:ui[lang][0],exact:true}).waitFor();
   await page.getByText('SKU-1',{exact:false}).locator('visible=true').first().waitFor();
   const root=page.locator('main section').first();
   await page.addScriptTag({path:process.env.AXE_MODULE || require.resolve('axe-core/axe.min.js')});
   const violations=[];
   for (const label of ui[lang].slice(1)) {
    await root.getByRole('button',{name:label,exact:true}).click();
    await page.waitForTimeout(150);
    const check=await page.evaluate(async()=>await axe.run(document.querySelector('main section'),{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}}));
    violations.push(...check.violations.map(v=>({view:label,id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)})));
   }
   const overflow=await page.evaluate(()=>({page:document.documentElement.scrollWidth>innerWidth,section:document.querySelector('main section').getBoundingClientRect().right>innerWidth+1}));
   const row={lang,dark,width,errors,overflow,violations};results.push(row);
   await page.screenshot({path:`/tmp/yrys-ui-check/wms-${lang}-${dark?'dark':'light'}-${width}.png`,fullPage:true});
   console.log(JSON.stringify(row));
   await ctx.close();
  }
  fs.writeFileSync('/tmp/yrys-ui-check/results.json',JSON.stringify(results,null,2));
  assert(results.every(r=>!r.errors.length&&!r.violations.length&&!r.overflow.section),'Browser smoke detected errors, section overflow or axe violations');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
