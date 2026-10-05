const { createRequire } = require('node:module');
const path = require('node:path');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const { chromium } = createRequire(path.resolve(__dirname,'../frontend/package.json'))('playwright');

(async()=>{
  const browser=await chromium.launch({headless:true,channel:process.env.PLAYWRIGHT_CHANNEL||'msedge'});
  const page=await browser.newPage({viewport:{width:1440,height:1080}});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const output=path.resolve(__dirname,'../artifacts'); fs.mkdirSync(output,{recursive:true});
  async function visibleRaster(fragment) {
    await page.waitForFunction(fragment=>[...document.querySelectorAll('img.leaflet-image-layer')].some(i=>i.src.includes(fragment)&&i.complete&&i.naturalWidth>0),fragment);
  }
  try {
    await page.goto('http://127.0.0.1:8000',{waitUntil:'networkidle'});
    await page.getByLabel('Run evidence overlay').selectOption('clay');
    await visibleRaster('context_clay.png');
    await page.getByRole('button',{name:'Environmental evidence',exact:true}).click();
    await page.getByRole('heading',{name:'Dated rainfall',exact:true}).waitFor();
    await page.getByLabel('Rainfall grid cell').selectOption('2');
    await page.getByText('Monthly totals and completeness',{exact:true}).click();
    assert.equal(await page.locator('.environmental-rain tbody tr').count(),24);
    assert.equal(await page.locator('.environment-cards section').count(),4);
    await visibleRaster('/image/ndvi');
    await page.getByLabel('Observation window').selectOption('2025-1');
    await visibleRaster('/season/2025/1/ndvi');
    await page.getByLabel('Evidence layer',{exact:true}).selectOption('ndwi');
    await visibleRaster('/season/2025/1/ndwi');
    for(const layer of ['clay','infiltration','occurrence','transitions']) {
      await page.getByLabel('Evidence layer',{exact:true}).selectOption(layer);
      await visibleRaster(`/image/${layer}`);
    }
    assert.equal(await page.locator('.transition-legend span').count(),10);
    await page.locator('.comparison-metrics strong').first().filter({hasText:/[1-9]/}).waitFor();
    const samples=Number(await page.locator('.comparison-metrics strong').first().textContent());
    assert(samples>0,'Expected independent reference sites');
    await page.getByText('Inspect reference sample locations',{exact:true}).click();
    await page.locator('.reference-map .leaflet-container').waitFor();
    await page.screenshot({path:path.join(output,'environment-desktop.png'),fullPage:true});
    await page.getByLabel('Reference source').selectOption('field');
    await page.getByLabel('Observed outcome').selectOption('water_storage_suitability');
    await page.getByText('Insufficient comparison samples',{exact:true}).waitFor();
    assert.equal(await page.locator('.comparison-metrics strong').first().textContent(),'0');
    await page.getByText('Import independent field records',{exact:true}).click();
    await page.getByLabel('Field validation JSON').setInputFiles({name:'invalid.json',mimeType:'application/json',buffer:Buffer.from('[{"id":"invalid"}]')});
    await page.locator('.environment-page [role="alert"]').waitFor();
    await page.getByRole('link',{name:'Reference comparison JSON',exact:true}).waitFor();
    const exportLink=page.getByRole('link',{name:'NDVI · 2025 Q1 GeoTIFF',exact:true});
    const [download]=await Promise.all([page.waitForEvent('download'),exportLink.click()]);
    await download.saveAs(path.join(output,'environment-season-export.tif'));
    assert(fs.statSync(path.join(output,'environment-season-export.tif')).size>1000);
    await page.getByRole('button',{name:'Reload catalogue',exact:true}).click();
    await page.getByLabel('Reference source').selectOption('satellite');
    await page.locator('.comparison-metrics strong').first().filter({hasText:/[1-9]/}).waitFor();
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:path.join(output,'environment-mobile.png'),fullPage:true});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Mobile evidence overflow');
    await page.getByRole('button',{name:'Research atlas',exact:true}).click();
    await page.getByLabel('Find a heritage site').fill('Brihadishwara');
    await page.getByRole('button',{name:'Explore site',exact:true}).click();
    await page.getByRole('heading',{name:'Brihadishwara Temple',exact:true}).waitFor();
    await page.getByText('Acquired environmental context at this site',{exact:true}).click();
    await page.getByText('Surface soil clay',{exact:true}).waitFor();
    assert.deepEqual(errors,[],'Browser runtime errors');
    console.log('Environmental browser checks passed: sources, rainfall, all six layers, seasons, frozen exports, reference comparison, invalid imports, site context and mobile layout.');
  } finally {await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
