// Loop 14 export verification: PNG + CSV export buttons work.
const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');
const os = require('os');

const CHROME = path.join(process.env.HOME, 'Library/Caches/ms-playwright/chromium_headless_shell-1223/chrome-headless-shell-mac-arm64/chrome-headless-shell');
const HTML = 'file://' + path.resolve(process.argv[2] || 'reports/fx_flow_dashboard.html');

(async () => {
    const browser = await puppeteer.launch({
        executablePath: CHROME, headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
    });
    const dlDir = fs.mkdtempSync(path.join(os.tmpdir(), 'fxexp-'));
    let ok = true;
    try {
        const page = await browser.newPage();
        await page.setViewport({width: 1280, height: 720});
        const client = await page.target().createCDPSession();
        await client.send('Page.setDownloadBehavior', {behavior: 'allow', downloadPath: dlDir});
        await page.goto(HTML, {waitUntil: 'networkidle0'});
        await new Promise(r => setTimeout(r, 1500));

        const pngBtn = await page.$('[data-export="png"]');
        if (!pngBtn) { ok = false; console.log('FAIL: no PNG button'); }
        else { await pngBtn.click(); await new Promise(r => setTimeout(r, 1500)); }
        const pngFiles = fs.readdirSync(dlDir).filter(f => f.endsWith('.png'));

        const csvBtn = await page.$('[data-export="csv"]');
        if (!csvBtn) { ok = false; console.log('FAIL: no CSV button'); }
        else { await csvBtn.click(); await new Promise(r => setTimeout(r, 1500)); }
        const csvFiles = fs.readdirSync(dlDir).filter(f => f.endsWith('.csv'));

        const navCount = await page.$$eval('.nav-btn', bs => bs.length);

        let csvHasData = false;
        for (const f of csvFiles) {
            const content = fs.readFileSync(path.join(dlDir, f), 'utf-8');
            if (content.split('\n').filter(l => l.trim()).length > 1) csvHasData = true;
        }

        console.log('PNG files:', pngFiles.length);
        console.log('CSV files:', csvFiles.length, 'hasData:', csvHasData);
        console.log('nav modules:', navCount);
        ok = ok && pngFiles.length >= 1 && csvFiles.length >= 1 && csvHasData && navCount === 9;
        console.log('RESULT:', ok ? 'PASS' : 'FAIL');
        for (const f of [...pngFiles, ...csvFiles]) { try { fs.unlinkSync(path.join(dlDir, f)); } catch(e){} }
        fs.rmdirSync(dlDir);
        process.exit(ok ? 0 : 1);
    } finally {
        await browser.close();
    }
})();
