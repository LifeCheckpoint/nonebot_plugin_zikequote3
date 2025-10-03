const puppeteer = require('puppeteer');
const process = require('process');

(async () => {
  const args = process.argv.slice(2);

  const saveName = args[0] || 'screenshot.png';
  const htmlFilePath = args[1]; // 绝对路径
  const width = parseInt(args[2]) || 1000;
  const height = parseInt(args[3]) || 800;
  const deviceScaleFactor = parseFloat(args[4]) || 2.5;

  if (!htmlFilePath) {
    console.error("HTML 绝对路径应该作为第二个传入参数");
    process.exit(1);
  }


  const browser = await puppeteer.launch();
  const page = await browser.newPage();

  await page.setViewport({
    width: width,
    height: height,
    deviceScaleFactor: deviceScaleFactor
  });

  const fileUrl = `file://${htmlFilePath}`;

  try {
    await page.goto(fileUrl, { waitUntil: 'networkidle0' });
    await page.screenshot({
      path: saveName,
      fullPage: true
    });

    console.log('screenshot saved');
  } catch (error) {
    console.error('Error during screenshot:', error);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();