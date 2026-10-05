const {createRequire}=require('node:module');
const path=require('node:path');
const assert=require('node:assert/strict');
const {chromium}=createRequire(path.resolve(__dirname,'../frontend/package.json'))('playwright');

(async()=>{
  const browser=await chromium.launch({headless:true,channel:process.env.PLAYWRIGHT_CHANNEL||'msedge'});
  const page=await browser.newPage({viewport:{width:1440,height:1080}});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  let offline=true,failReport=false;
  await page.route('**/api/**',async route=>{
    if(offline)return route.abort('connectionrefused');
    if(failReport&&/\/api\/runs\/[^/?]+$/.test(route.request().url()))return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Simulated report outage'})});
    return route.continue();
  });
  try {
    await page.goto('http://127.0.0.1:8000',{waitUntil:'domcontentloaded'});
    await page.getByTestId('api-status').filter({hasText:'offline'}).waitFor();
    offline=false;
    await page.getByTestId('api-status').filter({hasText:'connected'}).waitFor({timeout:15000});
    await page.getByRole('link',{name:'GeoTIFF',exact:true}).waitFor();
    // A loaded page must stop claiming connectivity when the server disappears.
    offline=true;
    await page.getByTestId('api-status').filter({hasText:'offline'}).waitFor({timeout:15000});
    offline=false;failReport=true;
    await page.getByTestId('api-status').filter({hasText:'connected'}).waitFor({timeout:15000});
    await page.getByRole('alert').filter({hasText:'Simulated report outage'}).waitFor();
    failReport=false;
    await page.getByRole('button',{name:'Retry',exact:true}).click();
    await page.getByRole('link',{name:'GeoTIFF',exact:true}).waitFor();
    assert.equal(await page.getByRole('alert').count(),0);
    await page.screenshot({path:path.resolve(__dirname,'../artifacts/final-preview.png'),fullPage:true});
    assert.deepEqual(errors,[]);
    console.log('Recovery checks passed: initial outage, live disconnect detection, automatic reconnection and selected-run retry.');
  } finally {await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
