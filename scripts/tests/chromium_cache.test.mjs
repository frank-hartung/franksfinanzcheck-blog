import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, writeFileSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import { withChromiumExtractionLock } from '../chromium_cache.mjs';

const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

function tempDir() {
  return mkdtempSync(join(tmpdir(), 'ff-chromium-lock-test-'));
}

test('serialisiert parallele Erst-Extraktionen', async t => {
  const directory = tempDir();
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  let active = 0;
  let maxActive = 0;

  const extract = label => withChromiumExtractionLock(directory, async () => {
    active += 1;
    maxActive = Math.max(maxActive, active);
    await pause(80);
    active -= 1;
    return label;
  });

  assert.deepEqual(await Promise.all([extract('a'), extract('b')]), ['a', 'b']);
  assert.equal(maxActive, 1, 'Chromium-Archive wurden gleichzeitig entpackt');
  assert.equal(existsSync(join(directory, '.chromium-extract.lock')), false);
});

test('räumt einen Lock eines beendeten Prozesses auf', async t => {
  const directory = tempDir();
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  const lock = join(directory, '.chromium-extract.lock');
  writeFileSync(lock, JSON.stringify({ pid: 2_147_483_647, created: Date.now() }));

  assert.equal(await withChromiumExtractionLock(directory, async () => 'freigegeben'), 'freigegeben');
  assert.equal(existsSync(lock), false);
});
