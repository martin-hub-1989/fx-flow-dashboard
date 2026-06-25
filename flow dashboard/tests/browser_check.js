// Loop 12 browser verification: check 390px + 1280px no overflow, console errors
const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');

const CHROME = path.join(process.env.HOME, 'Library/Caches/ms-playwright/chromium_headless_shell-1223/chrome-headless-shell-mac-arm64/chrome-headless-shell');
const HTML = 'file://' + path.resolve('reports/fx_flow_dashboard.html');

async function checkViewport(browser, width, height) {
    const page = await browser.newPage();
    await page.setViewport({width, height, deviceScaleFactor: 1});
    const consoleErrors = [];
    page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
    page.on('pageerror', err => consoleErrors.push('PAGEERROR: ' + err.message));

    await page.goto(HTML, {waitUntil: 'networkidle0', timeout: 30000});
    await new Promise(r => setTimeout(r, 1500));

    // Click first module already active. Check scrollWidth vs clientWidth.
    const result = await page.evaluate(() => {
        const body = document.body;
        const html = document.documentElement;
        const overflow = {
            bodyScrollWidth: body.scrollWidth,
            bodyClientWidth: body.clientWidth,
            htmlScrollWidth: html.scrollWidth,
            htmlClientWidth: html.clientWidth,
            hasHorizontalOverflow: body.scrollWidth > body.clientWidth,
        };
        // Count rendered canvases
        const canvases = document.querySelectorAll('canvas').length;
        // Check a module rendered (charts)
        const activeModule = document.querySelector('.module.active');
        const chartsInActive = activeModule ? activeModule.querySelectorAll('.chart-card').length : 0;
        return {overflow, canvases, chartsInActive};
    });
    await page.close();
    return {viewport: `${width}x${height}`, result, consoleErrors: consoleErrors.slice(0, 5)};
}

(async () => {
    if (!fs.existsSync(CHROME)) {
        console.error('chrome-headless-shell not found');
        process.exit(2);
    }
    const browser = await puppeteer.launch({
        executablePath: CHROME,
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
    });
    try {
        // Desktop
        const desktop = await checkViewport(browser, 1280, 720);
        console.log('=== 1280x720 (desktop) ===');
        console.log('  overflow:', desktop.result.overflow);
        console.log('  canvases:', desktop.result.canvases, '| charts in active:', desktop.result.chartsInActive);
        console.log('  console errors:', desktop.consoleErrors.length, desktop.consoleErrors);

        // Mobile
        const mobile = await checkViewport(browser, 390, 844);
        console.log('\n=== 390x844 (mobile) ===');
        console.log('  overflow:', mobile.result.overflow);
        console.log('  hasHorizontalOverflow:', mobile.result.overflow.hasHorizontalOverflow);
        console.log('  canvases:', mobile.result.canvases, '| charts in active:', mobile.result.chartsInActive);
        console.log('  console errors:', mobile.consoleErrors.length, mobile.consoleErrors);

        // Switch through all 9 modules on mobile to ensure no overflow
        const page = await browser.newPage();
        await page.setViewport({width: 390, height: 844});
        await page.goto(HTML, {waitUntil: 'networkidle0'});
        const overflowMods = [];
        const navBtns = await page.$$eval('.nav-btn', btns => btns.map(b => b.textContent));
        for (const name of navBtns) {
            await page.evaluate(n => {
                const btn = [...document.querySelectorAll('.nav-btn')].find(b => b.textContent === n);
                if (btn) btn.click();
            }, name);
            await new Promise(r => setTimeout(r, 1200));
            const ov = await page.evaluate(() => document.body.scrollWidth > document.body.clientWidth);
            if (ov) overflowMods.push(name);
        }
        await page.close();
        console.log('\n=== 390px all 9 modules overflow check ===');
        console.log('  modules with horizontal overflow:', overflowMods.length, overflowMods);

        const pass = !desktop.result.overflow.hasHorizontalOverflow && !mobile.result.overflow.hasHorizontalOverflow && overflowMods.length === 0 && desktop.consoleErrors.length === 0;
        console.log('\n=== RESULT:', pass ? '✅ PASS' : '❌ FAIL', '===');
        process.exit(pass ? 0 : 1);
    } finally {
        await browser.close();
    }
})();
