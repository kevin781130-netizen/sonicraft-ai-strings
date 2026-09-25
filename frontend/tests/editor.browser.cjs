// Run with Playwright installed and editor_server.py listening on EDITOR_URL.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox']});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1000}});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(process.env.EDITOR_URL||'http://127.0.0.1:8765');
    await page.waitForFunction(()=>document.querySelector('#noteCount').textContent==='20 notes');
    async function snapshot(){
      const pending=page.waitForEvent('download');await page.click('#saveProject');
      const download=await pending;return JSON.parse(await fs.readFile(await download.path(),'utf8'));
    }
    const original=await snapshot();
    await page.click('#selectTrack');assert.equal(await page.textContent('#selectionCount'),'12 selected');
    await page.click('#scaleNotes');const scaled=await snapshot();
    assert.equal(scaled.notes[1].start,original.notes[1].start*2);
    assert.equal(scaled.notes[0].duration,original.notes[0].duration*2);
    assert.deepEqual(scaled.notes.filter(n=>n.track===1),original.notes.filter(n=>n.track===1));
    await page.click('#undo');assert.deepEqual((await snapshot()).notes,original.notes);
    await page.click('#redo');assert.deepEqual((await snapshot()).notes,scaled.notes);
    await page.click('#undo');
    await page.fill('#viewBar','4');await page.locator('#viewBar').press('Tab');
    await page.fill('#viewPitch','90');await page.locator('#viewPitch').press('Tab');
    const fixture={...original,notes:[{...original.notes[0],id:'a',start:10,duration:.95},{...original.notes[0],id:'b',start:11,duration:1}]};
    await page.setInputFiles('#importFile',{name:'fixture.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(fixture))});
    await page.waitForFunction(()=>document.querySelector('#noteCount').textContent==='2 notes');
    assert.equal(await page.textContent('#selectionCount'),'0 selected');
    await page.selectOption('#noteScope','track');await page.fill('#gapThreshold','0.1');await page.click('#closeGaps');
    assert.equal((await snapshot()).notes[0].duration,1);
    await page.click('#undo');assert.equal((await snapshot()).notes[0].duration,.95);
    await page.check('#skipSilence');await page.click('#previewPlay');
    await page.waitForFunction(()=>document.querySelector('#previewPlay').textContent.includes('PAUSE'));
    await page.waitForTimeout(200);assert.ok((await page.textContent('#playPosition')).startsWith('3:'));
    await page.click('#previewPlay');assert.match(await page.textContent('#previewPlay'),/PREVIEW/);
    await page.click('#previewStop');assert.equal(await page.textContent('#playPosition'),'1:1.00');
    // Modifier selection is exercised using real pointer events at note coordinates.
    await page.fill('#viewBar','3');await page.locator('#viewBar').press('Tab');
    await page.fill('#viewPitch','84');await page.locator('#viewPitch').press('Tab');
    const box=await page.locator('#piano').boundingBox();
    const y=box.y+24+(84-fixture.notes[0].pitch)*16+7;
    await page.mouse.click(box.x+54+2*56+10,y);
    await page.keyboard.down('Shift');await page.mouse.click(box.x+54+3*56+10,y);await page.keyboard.up('Shift');
    assert.equal(await page.textContent('#selectionCount'),'2 selected');
    await page.locator('#piano').click({position:{x:400,y:40}}); // clear via empty grid
    await page.click('#selectTrack');await page.locator('#piano').dispatchEvent('focus');
    await page.evaluate(()=>document.activeElement.blur());await page.keyboard.press('Delete');
    assert.equal(await page.textContent('#noteCount'),'0 notes');await page.click('#undo');
    assert.equal(await page.textContent('#noteCount'),'2 notes');
    for(const width of [1440,1024,720,390]){
      await page.setViewportSize({width,height:1000});
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`overflow at ${width}`);
      assert.ok(await page.evaluate(()=>{const main=document.querySelector('.main').getBoundingClientRect(),bar=document.querySelector('#artbar').getBoundingClientRect();return bar.bottom<=main.bottom+1}),`clipped editor at ${width}`);
    }
    await page.setViewportSize({width:1440,height:1000});
    if(process.env.EDITOR_SCREENSHOT)await page.screenshot({path:process.env.EDITOR_SCREENSHOT,fullPage:true});
    assert.deepEqual(errors,[]);console.log('PASS: browser selection, scaling, gaps, undo/redo, import/save, preview, navigation, responsive layout');
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
