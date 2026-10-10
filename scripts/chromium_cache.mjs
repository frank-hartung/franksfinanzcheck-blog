import {
  closeSync,
  mkdirSync,
  openSync,
  readFileSync,
  statSync,
  unlinkSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { setTimeout as sleep } from 'node:timers/promises';

const TEMP_BASE = tmpdir();

/**
 * Put Sparticuz's hard-coded `$TMPDIR/chromium` cache under a versioned path.
 * Without this, package upgrades can silently reuse an older extracted binary.
 */
export function prepareChromiumTemp(version) {
  if (!/^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$/.test(String(version || ''))) {
    throw new Error(`Ungültige Chromium-Paketversion: ${String(version)}`);
  }
  const directory = join(TEMP_BASE, 'franksfinanzcheck-chromium', version);
  mkdirSync(directory, { recursive: true });
  process.env.TMPDIR = directory;
  return directory;
}

function lockOwnerAlive(lockPath) {
  try {
    const info = JSON.parse(readFileSync(lockPath, 'utf8'));
    if (!Number.isInteger(info.pid) || info.pid < 1) {
      return Date.now() - statSync(lockPath).mtimeMs < 30_000;
    }
    try {
      process.kill(info.pid, 0);
      return true;
    } catch (error) {
      return error?.code !== 'ESRCH';
    }
  } catch (error) {
    if (error?.code === 'ENOENT') return false;
    try {
      return Date.now() - statSync(lockPath).mtimeMs < 30_000;
    } catch {
      return false;
    }
  }
}

/**
 * Serialize Brotli extraction. Sparticuz uses fixed filenames and returns as
 * soon as a partially-created file exists, so concurrent first launches can
 * otherwise fail with ETXTBSY. Crashed owners are reclaimed automatically.
 */
export async function withChromiumExtractionLock(directory, operation, timeoutMs = 120_000) {
  const lockPath = join(directory, '.chromium-extract.lock');
  const deadline = Date.now() + timeoutMs;
  let lockFd;

  while (lockFd === undefined) {
    try {
      lockFd = openSync(lockPath, 'wx', 0o600);
      writeFileSync(lockFd, JSON.stringify({ pid: process.pid, created: Date.now() }));
    } catch (error) {
      if (lockFd !== undefined) {
        try { closeSync(lockFd); } catch {}
        lockFd = undefined;
        try { unlinkSync(lockPath); } catch {}
      }
      if (error?.code !== 'EEXIST') throw error;
      if (!lockOwnerAlive(lockPath)) {
        try { unlinkSync(lockPath); } catch {}
        continue;
      }
      if (Date.now() >= deadline) {
        throw new Error(`Timeout beim Warten auf Chromium-Extraktion (${lockPath})`);
      }
      await sleep(100);
    }
  }

  try {
    return await operation();
  } finally {
    try { closeSync(lockFd); } catch {}
    try { unlinkSync(lockPath); } catch {}
  }
}
