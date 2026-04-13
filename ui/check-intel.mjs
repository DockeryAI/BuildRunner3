import { chromium } from 'playwright';

const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto('http://localhost:4400');
await page.waitForTimeout(1000);
await page.click('[data-ws="intel"]');
await page.waitForTimeout(1500);

// Click on Deals tab
await page.click('button[data-iws-tab="deals"]');
await page.waitForTimeout(1500);

// Click on Bought tab
await page.click('button[data-deals-status="bought"]');
await page.waitForTimeout(1500);

await page.screenshot({ path: '/tmp/intel-ws.png', fullPage: true });
console.log('Screenshot saved to /tmp/intel-ws.png');
await browser.close();
