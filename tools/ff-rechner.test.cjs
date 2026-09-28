const assert = require('node:assert/strict');
const fs = require('node:fs');
const test = require('node:test');
const vm = require('node:vm');

function loadLogic() {
  const context = { console };
  context.globalThis = context;
  vm.createContext(context);
  vm.runInContext(
    fs.readFileSync('static/premium/ff-rechner.js', 'utf8'),
    context,
    { filename: 'ff-rechner.js' },
  );
  return context.FFRechnerLogik;
}

test('Notgroschen-Rechner rechnet mit notwendigen Monatsausgaben, nicht Einkommen', () => {
  const logic = loadLogic();
  const result = logic.notgroschen({ ausgaben: '1.800', erspartes: '4.000', reserve: '3' });

  assert.equal(result.ziel, 5400);
  assert.equal(result.luecke, 1400);
  assert.equal(result.rate12, 1400 / 12);
  assert.equal(result.rate24, 1400 / 24);
  assert.equal(result.fertig, false);
});

test('Notgroschen-Rechner akzeptiert eine bereits gefüllte Reserve', () => {
  const logic = loadLogic();
  const result = logic.notgroschen({ ausgaben: '1500', erspartes: '9000', reserve: '6' });

  assert.equal(result.ziel, 9000);
  assert.equal(result.luecke, 0);
  assert.equal(result.fertig, true);
});

test('Notgroschen-Rechner weist unvollständige oder unbrauchbare Eingaben zurück', () => {
  const logic = loadLogic();

  assert.equal(logic.notgroschen({ ausgaben: '', reserve: '3' }), null);
  assert.equal(logic.notgroschen({ ausgaben: '1800', reserve: '0' }), null);
});
