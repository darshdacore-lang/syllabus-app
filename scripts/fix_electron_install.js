const { downloadArtifact } = require('@electron/get');
const extract = require('extract-zip');
const fs = require('fs');
const path = require('path');

(async () => {
  try {
    const version = '30.5.1';
    const arch = 'arm64';
    const platform = 'darwin';
    const electronDir = path.join(process.cwd(), 'node_modules', 'electron');
    const distDir = path.join(electronDir, 'dist');
    fs.rmSync(distDir, { recursive: true, force: true });
    fs.mkdirSync(distDir, { recursive: true });
    const zipPath = await downloadArtifact({
      version,
      artifactName: 'electron',
      platform,
      arch,
      checksums: require(path.join(electronDir, 'checksums.json')),
    });
    console.log('downloaded zip:', zipPath);
    await extract(zipPath, { dir: distDir });
    console.log('extract complete');
    fs.writeFileSync(path.join(electronDir, 'path.txt'), 'Electron.app/Contents/MacOS/Electron');
    fs.writeFileSync(path.join(distDir, 'version'), version);
    console.log('electron install fixed');
  } catch (error) {
    console.error('ERROR', error);
    process.exit(1);
  }
})();
