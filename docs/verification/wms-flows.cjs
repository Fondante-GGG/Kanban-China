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
 const browser=await chromium.launch({headless:true});
 try {
  const ctx=await browser.newContext({viewport:{width:360,height:900}});
  await ctx.addInitScript(()=>localStorage.setItem('kanban_token','fixture'));
  const page=await ctx.newPage();const calls=[];let revoke=false, conflict=false;
  await page.route('**/api/**',async route=>{
   const path=new URL(route.request().url()).pathname.replace(/^\/api\//,'');let data={};
   const verb=route.request().method();
   if(path==='auth/me')data={id:2,email:'wms@test',full_name:'Tester',role:'employee',department_id:1,interface_language:'ru',assigned_board_id:null,system_permissions:perms};
   else if(path==='boards')data={boards:[]};
   else if(path==='notifications')data={notifications:[]};
   else if(path.startsWith('warehouse/')){
    if(revoke)return route.fulfill({status:403,contentType:'application/json',body:JSON.stringify({code:'permission_denied',error:'denied'})});
    if(verb==='POST'){
     const payload=route.request().postDataJSON();calls.push({path,payload});
     if(path==='warehouse/receipts/1/post'){
      fixture.receipts.items[0].status='posted';fixture.receipts.items[0].allowed_actions=[];data={id:1,status:'posted'};
      if(conflict)return route.fulfill({status:409,contentType:'application/json',body:JSON.stringify({code:'conflict',error:'Already posted'})});
     }
     else if(path==='warehouse/counts/1/approve'){fixture.counts.items[0].status='approved';fixture.counts.items[0].allowed_actions=[];data={id:1,status:'approved'};}
     else data={id:2,status:path.endsWith('counts')?'counted':'draft'};
    }else data=path==='warehouse/alerts/expiry'?fixture.expiry:fixture[path.split('/')[1]]||{};
   }
   await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(data)});
  });
  await page.goto(process.env.UI_BASE_URL || 'http://127.0.0.1:3015');
  await page.getByRole('button',{name:'Склад',exact:true}).click();
  const root=page.locator('main section').first();
  await root.getByRole('button',{name:'Приёмки',exact:true}).click();
  await root.getByRole('button',{name:'Новая приёмка',exact:true}).click();
  let form=root.locator('form');
  await form.getByLabel('Номер документа *',{exact:true}).fill('REC-BROWSER');
  await form.getByLabel(/^Заказ/).selectOption('1');
  await form.getByLabel(/^Товар \/ SKU/).selectOption('1');
  await form.getByLabel('Количество *',{exact:true}).fill('9');
  await form.getByRole('button',{name:'Сохранить',exact:true}).click();
  await root.getByRole('alert').waitFor();
  assert.equal(calls.length,0,'Partial receipt without a reason must not submit');
  await form.getByLabel('Причина расхождения',{exact:true}).fill('Недопоставка');
  await page.addScriptTag({path:process.env.AXE_MODULE || require.resolve('axe-core/axe.min.js')});
  let check=await page.evaluate(async()=>axe.run(document.querySelector('main section'),{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}}));
  assert.equal(check.violations.length,0,JSON.stringify(check.violations.map(v=>v.id)));
  await form.getByRole('button',{name:'Сохранить',exact:true}).click();
  await page.waitForFunction(()=>!document.querySelector('main section form'));
  assert.equal(calls[0].payload.items[0].qty,9);assert(!('unit_cost' in calls[0].payload.items[0]));
  await root.getByRole('button',{name:'Открыть',exact:true}).click();
  await root.getByRole('button',{name:'Закрыть детали',exact:true}).click();
  assert.equal(await page.evaluate(()=>document.activeElement.textContent),'Открыть');
  await root.getByRole('button',{name:'Открыть',exact:true}).click();
  await root.getByRole('button',{name:'Провести приёмку',exact:true}).click();
  await root.getByRole('button',{name:'Провести приёмку',exact:true}).waitFor({state:'hidden'});
  await root.getByRole('button',{name:'Закрыть детали',exact:true}).click();
  assert(['Открыть','Склад'].includes(await page.evaluate(()=>document.activeElement.textContent)));
  await root.getByRole('button',{name:'Инвентаризации',exact:true}).click();
  await root.getByRole('button',{name:'Новая инвентаризация',exact:true}).click();
  form=root.locator('form');
  await form.getByLabel('Номер документа *',{exact:true}).fill('CNT-BROWSER');
  await form.getByLabel(/^Товар \/ SKU/).selectOption('1');
  await form.getByLabel('Фактический остаток *',{exact:true}).fill('9');
  await form.getByLabel('Причина расхождения',{exact:true}).fill('Пересчёт');
  await form.getByRole('button',{name:'Сохранить',exact:true}).click();
  await page.waitForFunction(()=>!document.querySelector('main section form'));
  assert(calls.some(x=>x.path==='warehouse/counts'&&x.payload.items[0].actual_qty==='9'));
  await root.getByRole('button',{name:'Открыть',exact:true}).click();
  await root.getByRole('button',{name:'Утвердить расхождения',exact:true}).click();
  await root.getByRole('button',{name:'Утвердить расхождения',exact:true}).waitFor({state:'hidden'});
  fixture.receipts.items[0].status='draft';fixture.receipts.items[0].allowed_actions=['post'];conflict=true;
  await root.getByRole('button',{name:'Движения',exact:true}).click();
  await root.getByRole('button',{name:'Открыть',exact:true}).click();
  await root.getByRole('button',{name:'Провести приёмку',exact:true}).click();
  await root.getByRole('alert').waitFor();
  await root.getByRole('button',{name:'Провести приёмку',exact:true}).waitFor({state:'hidden'});
  revoke=true;
  await root.getByRole('button',{name:'Обновить',exact:true}).click();
  await root.getByRole('alert').waitFor();
  assert.equal(await root.getByRole('button',{name:'Новая инвентаризация',exact:true}).count(),0);
  console.log(JSON.stringify({result:'PASS',flows:['partial receipt validation','receipt create without costs','receipt post and refresh','close focus restoration','count create and approve','movement source exact refresh on 409','revoked permission clears actions'],posts:calls.length}));
  await ctx.close();
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
