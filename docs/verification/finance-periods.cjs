// Browser checks against mock APIs; no working finance records are modified.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs');
const {context,state,axeCheck}=require('./supplier-returns-smoke.cjs');
async function routes(page,s){
 await page.route('**/api/auth/me',r=>r.fulfill({contentType:'application/json',body:JSON.stringify({id:4,email:'period@test',full_name:'Finance',role:'accountant',department_id:1,interface_language:s.lang,assigned_board_id:null,system_permissions:['finance.payable.read',...(s.canClose?['finance.period.close']:[])]})}));
 await page.route('**/api/finance/periods**',async r=>{
  const req=r.request(),u=new URL(req.url());if(s.denied)return r.fulfill({status:403,contentType:'application/json',body:JSON.stringify({code:'permission_denied'})});
  if(req.method()==='GET'){const year=Number(u.searchParams.get('year'));return r.fulfill({contentType:'application/json',body:JSON.stringify({year,can_close:s.canClose,items:Array.from({length:12},(_,i)=>({year,month:i+1,is_closed:!!s.closed[`${year}-${i+1}`],closed_by_name:s.closed[`${year}-${i+1}`]?'Finance':null,closed_at:s.closed[`${year}-${i+1}`]?'2026-10-31T10:00:00Z':null,close_reason:s.closed[`${year}-${i+1}`]||''}))})});}
  const [year,month]=u.pathname.match(/periods\/(\d+)\/(\d+)\/close/).slice(1).map(Number),body=req.postDataJSON(),key=`${year}-${month}`;s.posts.push({year,month,body});s.closed[key] ||=body.reason;
  if(s.lost){s.lost=false;return r.abort('failed');}
  return r.fulfill({contentType:'application/json',body:JSON.stringify({year,month,is_closed:true,closed_by_name:'Finance',closed_at:'2026-10-31T10:00:00Z',close_reason:s.closed[key]})});
 });
}
module.exports={routes};

const labels={"ru": {"title": "Финансовые периоды", "close": "Закрыть месяц", "reason": "Основание закрытия", "check": "Проверить закрытие", "confirm": "Подтвердить закрытие месяца", "closedSuccess": "Период закрыт", "readOnly": "Доступно чтение. Право закрытия месяца отсутствует.", "forbidden": "Доступ к финансовым периодам запрещён.", "year": "Год", "show": "Показать год"}, "ky": {"title": "Финансылык мезгилдер", "close": "Айды жабуу", "reason": "Жабуунун негизи", "check": "Жабууну текшерүү", "confirm": "Айдын жабылышын ырастоо", "closedSuccess": "Мезгил жабык", "readOnly": "Окууга уруксат бар. Айды жабууга укук жок.", "forbidden": "Финансылык мезгилдерге кирүүгө уруксат жок.", "year": "Жыл", "show": "Жылды көрсөтүү"}, "zh-Hans": {"title": "财务期间", "close": "关闭月份", "reason": "关闭依据", "check": "核对关闭操作", "confirm": "确认关闭月份", "closedSuccess": "财务期间已关闭", "readOnly": "您可以查看期间，但没有关闭月份的权限。", "forbidden": "无权访问财务期间。", "year": "年份", "show": "显示年份"}, "zh-Hant": {"title": "財務期間", "close": "關閉月份", "reason": "關閉依據", "check": "核對關閉操作", "confirm": "確認關閉月份", "closedSuccess": "財務期間已關閉", "readOnly": "您可以查看期間，但沒有關閉月份的權限。", "forbidden": "無權存取財務期間。", "year": "年份", "show": "顯示年份"}};
async function open(browser,s,dark=false,width=360){
 const x=await context(browser,state('posted'),'finance',s.lang,dark,width,({page})=>routes(page,s));
 const root=x.page.getByRole('region',{name:labels[s.lang].title,exact:true});await root.getByRole('article').first().waitFor();return {...x,root};
}
async function preview(x,t){await x.root.getByRole('button',{name:t.close,exact:true}).first().click();await x.root.getByLabel(t.reason,{exact:true}).fill('Закрытие после проверки документов');await x.root.getByRole('button',{name:t.check,exact:true}).click();await x.root.getByRole('button',{name:t.confirm,exact:true}).waitFor();}
(async()=>{const browser=await chromium.launch({headless:true}),results=[];try{
 for(const lang of Object.keys(labels))for(const dark of[false,true])for(const width of[360,1440]){
 const s={lang,canClose:true,closed:{},posts:[]},x=await open(browser,s,dark,width),t=labels[lang];await preview(x,t);const violations=await axeCheck(x.page),overflow=await x.page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);assert.deepEqual(x.errors,[]);assert.deepEqual(violations,[]);assert.equal(overflow,false);await x.root.getByRole('button',{name:t.confirm,exact:true}).click();await x.root.getByText(t.closedSuccess+':',{exact:false}).waitFor();assert.equal(s.posts.length,1);assert.equal(await x.root.getByRole('button',{name:t.close,exact:true}).count(),11);results.push({lang,dark,width,violations,overflow,errors:x.errors});console.log(JSON.stringify(results.at(-1)));await x.ctx.close();
 }
 const s={lang:'ru',canClose:true,closed:{},posts:[],lost:true},x=await open(browser,s);await preview(x,labels.ru);await x.root.getByRole('button',{name:labels.ru.confirm,exact:true}).click();await x.root.getByText(labels.ru.closedSuccess+':',{exact:false}).waitFor();assert.equal(s.posts.length,1);assert.equal(Object.keys(s.closed).length,1);results.push({case:'lost-response-reread-existing-closure',ok:true});await x.ctx.close();
 const readonly={lang:'ru',canClose:false,closed:{},posts:[]},y=await open(browser,readonly);await y.root.getByText(labels.ru.readOnly,{exact:true}).waitFor();assert.equal(await y.root.getByRole('button',{name:labels.ru.close,exact:true}).count(),0);results.push({case:'readonly-no-close',ok:true});await y.ctx.close();
 const revoked={lang:'ru',canClose:true,closed:{},posts:[]},z=await open(browser,revoked);await preview(z,labels.ru);revoked.denied=true;await z.root.getByRole('button',{name:labels.ru.confirm,exact:true}).click();await z.root.getByText(labels.ru.forbidden,{exact:true}).waitFor();assert.equal(await z.root.getByRole('article').count(),0);assert.equal(revoked.posts.length,0);results.push({case:'revoked-access-clears-periods',ok:true});await z.ctx.close();
 fs.mkdirSync('/tmp/yrys-period-check',{recursive:true});fs.writeFileSync('/tmp/yrys-period-check/results.json',JSON.stringify(results,null,2));console.log('OK',results.length);
 }finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
