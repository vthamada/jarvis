import test from "node:test";
import assert from "node:assert/strict";
import {
  inspectPcmWav,
  MAX_WAV_BYTES,
  MAX_WAV_SECONDS,
} from "../local-voice-playback.mjs";

// Synthetic buffers only: no human audio, filesystem, model, network or device.
// Large boundary fixtures allocate their payload once, directly in the RIFF.
function tag(view, offset, name) {
  assert.equal(name.length, 4);
  for (let index = 0; index < 4; index++) {
    view.setUint8(offset + index, name.charCodeAt(index));
  }
}

function format({ channels = 1, rate = 8000, encoding = 1, bits = 16,
  align = channels * 2, byteRate = rate * channels * 2 } = {}) {
  const payload = new Uint8Array(16), view = new DataView(payload.buffer);
  view.setUint16(0, encoding, true);
  view.setUint16(2, channels, true);
  view.setUint32(4, rate, true);
  view.setUint32(8, byteRate, true);
  view.setUint16(12, align, true);
  view.setUint16(14, bits, true);
  return { name: "fmt ", payload };
}

function riff(chunks, { trailer = 0, growBy = 0 } = {}) {
  const sizeOf = (chunk) => chunk.size ?? chunk.payload?.byteLength ?? 0;
  const allocated = 12 + chunks.reduce((size, chunk) => {
    const bytes = sizeOf(chunk);
    return size + 8 + bytes + (bytes % 2 && chunk.pad !== false ? 1 : 0);
  }, 0) + trailer;
  const buffer = growBy ? new ArrayBuffer(allocated, { maxByteLength: allocated + growBy }) : new ArrayBuffer(allocated);
  const view = new DataView(buffer);
  tag(view, 0, "RIFF"); tag(view, 8, "WAVE");
  view.setUint32(4, allocated - 8, true);
  let offset = 12;
  for (const chunk of chunks) {
    const size = sizeOf(chunk);
    tag(view, offset, chunk.name);
    view.setUint32(offset + 4, chunk.declaredSize ?? size, true);
    if (chunk.payload) new Uint8Array(buffer, offset + 8, chunk.payload.byteLength).set(chunk.payload);
    offset += 8 + size;
    if (size % 2 && chunk.pad !== false) view.setUint8(offset++, chunk.padByte ?? 0);
  }
  return buffer;
}

function wav({ channels = 1, rate = 8000, frames = 8, prefix = [], between = [], suffix = [],
  first = -32768, last = 32767, formatOptions = {}, growBy = 0 } = {}) {
  const buffer = riff([
    ...prefix, format({ channels, rate, ...formatOptions }), ...between,
    { name: "data", size: frames * channels * 2 }, ...suffix,
  ], { growBy });
  let offset = 12;
  const view = new DataView(buffer);
  while (offset < buffer.byteLength) {
    const size = view.getUint32(offset + 4, true);
    const name = String.fromCharCode(...new Uint8Array(buffer, offset, 4));
    if (name === "data" && size) {
      view.setInt16(offset + 8, first, true);
      view.setInt16(offset + 8 + size - 2, last, true);
      break;
    }
    offset += 8 + size + size % 2;
  }
  return buffer;
}

function invalid(buffer) {
  assert.throws(() => inspectPcmWav(buffer), (error) => {
    assert.equal(error.message, "invalid_local_wav");
    return true;
  });
}

test("product bounds are exactly 600 seconds and 32 MiB", () => {
  assert.equal(MAX_WAV_SECONDS, 600);
  assert.equal(MAX_WAV_BYTES, 32 * 1024 * 1024);
});

for (const channels of [1, 2]) {
  for (const rate of [8000, 11025, 22050, 24000, 44100, 48000, 96000]) {
    test(`PCM16 ${channels} channel(s) at ${rate} Hz preserves exact samples and metadata`, () => {
      const buffer = wav({ channels, rate, frames: 9 });
      const result = inspectPcmWav(buffer);
      assert.deepEqual(result, {
        channels, rate, offset: 44, bytes: 9 * channels * 2, frames: 9, duration: 9 / rate,
      });
      assert.ok(Object.isFrozen(result));
      assert.deepEqual(Object.keys(result).sort(), ["bytes", "channels", "duration", "frames", "offset", "rate"]);
      const view = new DataView(buffer);
      assert.equal(view.getInt16(result.offset, true), -32768);
      assert.equal(view.getInt16(result.offset + result.bytes - 2, true), 32767);
      assert.equal(view.getInt16(result.offset + 2, true), 0);
      assert.throws(() => { result.frames = 123; }, TypeError);
    });
  }
}

for (const channels of [1, 2]) {
  test(`silence is legitimate PCM, ${channels} channel(s), without invented identity or authority`, () => {
    const result = inspectPcmWav(wav({ channels, first: 0, last: 0 }));
    assert.equal(result.channels, channels);
    assert.equal(result.frames, 8);
    assert.equal(result.duration, 0.001);
    assert.ok(!("authority" in result) && !("identity" in result) && !("source_origin" in result));
  });
}

test("600 second mono boundary accepted, one extra frame and 601 seconds rejected", () => {
  // Reuse one 9.6 MB payload for all duration boundaries; no repeated large allocation.
  const buffer = wav({ rate: 8000, frames: 8000 * 601, growBy: 1 });
  invalid(buffer);
  const view = new DataView(buffer);
  const exactSize = 44 + 8000 * 600 * 2;
  buffer.resize(exactSize);
  view.setUint32(4, buffer.byteLength - 8, true);
  view.setUint32(40, buffer.byteLength - 44, true);
  assert.equal(inspectPcmWav(buffer).duration, 600);
  buffer.resize(exactSize + 2);
  view.setUint32(4, buffer.byteLength - 8, true);
  view.setUint32(40, buffer.byteLength - 44, true);
  invalid(buffer);
  // Extra physical bytes cannot be ignored by declaring only the bounded RIFF.
  view.setUint32(4, exactSize - 8, true);
  invalid(buffer);
});

test("600 second stereo boundary accepted", () => {
  const buffer = wav({ channels: 2, rate: 8000, frames: 8000 * 600 });
  const result = inspectPcmWav(buffer);
  assert.equal(result.duration, 600);
  assert.equal(result.channels, 2);
  assert.equal(result.bytes, 8000 * 600 * 4);
});

test("121 seconds is now accepted rather than retaining the old single-part ceiling", () => {
  const result = inspectPcmWav(wav({ rate: 8000, frames: 8000 * 121 }));
  assert.equal(result.duration, 121);
  assert.equal(result.frames, 8000 * 121);
});

test("exact 32 MiB inclusive boundary accepted and one byte over refused", () => {
  // One resizable maximum-size allocation covers both sides of the bound.
  const exact = wav({ rate: 96000, frames: (MAX_WAV_BYTES - 44) / 2, growBy: 1 });
  assert.equal(exact.byteLength, MAX_WAV_BYTES);
  const result = inspectPcmWav(exact);
  assert.equal(result.bytes, MAX_WAV_BYTES - 44);
  assert.ok(result.duration < 600);
  exact.resize(MAX_WAV_BYTES + 1);
  // Correct the RIFF size: refusal is the byte ceiling, not a stale RIFF header.
  new DataView(exact).setUint32(4, exact.byteLength - 8, true);
  invalid(exact);
});

for (const value of [null, undefined, false, true, 44, "RIFF_PRIVATE_SOURCE", {}, [],
  new Uint8Array(44), new DataView(new ArrayBuffer(44)), Buffer.alloc(44),
  { byteLength: 44, slice() { throw new Error("PRIVATE_PATH"); } }]) {
  test(`non-ArrayBuffer input refused: ${value === null ? "null" : typeof value}/${value?.constructor?.name ?? "none"}`, () => {
    invalid(value);
  });
}

test("detached input is refused, not interpreted as a valid empty WAV", () => {
  const value = wav();
  structuredClone(value, { transfer: [value] });
  assert.equal(value.byteLength, 0);
  invalid(value);
});

for (const bytes of [0, 1, 11, 12, 35, 36, 43, 44]) {
  test(`headerless ${bytes} byte buffer refused`, () => invalid(new ArrayBuffer(bytes)));
}

const headerChanges = [
  ["big endian RIFX", (view) => tag(view, 0, "RIFX")],
  ["RF64 unsupported", (view) => tag(view, 0, "RF64")],
  ["non-WAVE subtype", (view) => tag(view, 8, "AVI ")],
  ["RIFF declared zero", (view) => view.setUint32(4, 0, true)],
  ["RIFF declared shorter", (view) => view.setUint32(4, 43, true)],
  ["RIFF declared longer", (view) => view.setUint32(4, 0xffffffff, true)],
  ["chunk size overflow", (view) => view.setUint32(40, 0xffffffff, true)],
  ["PCM data empty", (view) => view.setUint32(40, 0, true)],
  ["data declared too long", (view) => view.setUint32(40, 200, true)],
  ["data declared partial", (view) => view.setUint32(40, 2, true)],
  ["unknown fmt identifier", (view) => tag(view, 12, "Fmt ")],
  ["unknown data identifier", (view) => tag(view, 36, "Data")],
];
for (const [name, mutate] of headerChanges) {
  test(`malformed RIFF refused: ${name}`, () => {
    const buffer = wav(); mutate(new DataView(buffer)); invalid(buffer);
  });
}

const invalidFormats = [
  ["float", { encoding: 3 }], ["extensible", { encoding: 0xfffe }],
  ["compressed", { encoding: 6 }], ["zero encoding", { encoding: 0 }],
  ["zero channels", { channels: 0 }], ["three channels", { channels: 3 }],
  ["many channels", { channels: 65535 }], ["rate too low", { rate: 7999 }],
  ["rate too high", { rate: 96001 }], ["rate zero", { rate: 0 }],
  ["rate unsigned ceiling", { rate: 0xffffffff }],
  ["8 bit", { bits: 8 }], ["24 bit", { bits: 24 }], ["32 bit", { bits: 32 }],
  ["zero bits", { bits: 0 }], ["zero alignment", { align: 0 }],
  ["wrong mono alignment", { align: 4 }], ["unaligned mono", { align: 1 }],
  ["zero byte rate", { byteRate: 0 }], ["wrong byte rate", { byteRate: 15999 }],
  ["byte rate unsigned ceiling", { byteRate: 0xffffffff }],
];
for (const [name, options] of invalidFormats) {
  test(`invalid fmt refused: ${name}`, () => {
    invalid(riff([format(options), { name: "data", size: 16 }]));
  });
}

for (const size of [0, 1, 14, 15, 17, 18, 20, 40]) {
  test(`fmt payload size ${size} refused rather than partially interpreted`, () => {
    invalid(riff([{ name: "fmt ", size }, { name: "data", size: 16 }]));
  });
}

for (const channels of [1, 2]) {
  for (const size of [1, 3, 5, 7]) {
    test(`data ${size} bytes is not whole ${channels}-channel PCM16 frames`, () => {
      invalid(riff([format({ channels }), { name: "data", size }]));
    });
  }
}

test("stereo data must align to complete interleaved frames", () => {
  for (const size of [2, 6, 10]) invalid(riff([format({ channels: 2 }), { name: "data", size }]));
  const buffer = wav({ channels: 2, frames: 2 });
  const view = new DataView(buffer);
  view.setInt16(44, -32768, true); view.setInt16(46, 12345, true);
  view.setInt16(48, -23456, true); view.setInt16(50, 32767, true);
  const result = inspectPcmWav(buffer);
  assert.equal(result.frames, 2);
  assert.deepEqual([0, 1, 2, 3].map((index) => view.getInt16(result.offset + index * 2, true)),
    [-32768, 12345, -23456, 32767]);
});

const invalidLayouts = [
  ["missing fmt", [{ name: "data", size: 16 }]],
  ["missing data", [format()]],
  ["only unknown chunk", [{ name: "JUNK", size: 40 }]],
  ["data before fmt", [{ name: "data", size: 16 }, format()]],
  ["duplicate fmt before data", [format(), format(), { name: "data", size: 16 }]],
  ["duplicate fmt after data", [format(), { name: "data", size: 16 }, format()]],
  ["duplicate data", [format(), { name: "data", size: 16 }, { name: "data", size: 16 }]],
  ["duplicate empty data", [format(), { name: "data", size: 16 }, { name: "data", size: 0 }]],
  ["first data empty", [format(), { name: "data", size: 0 }, { name: "data", size: 16 }]],
];
for (const [name, chunks] of invalidLayouts) {
  test(`required chunk layout refused: ${name}`, () => invalid(riff(chunks)));
}

for (const trailer of [1, 2, 3, 4, 5, 6, 7]) {
  test(`RIFF trailing ${trailer} bytes is not a complete chunk header`, () => {
    invalid(riff([format(), { name: "data", size: 16 }], { trailer }));
  });
}

test("additional bytes outside declared RIFF refused even if a valid header preceded them", () => {
  const complete = wav();
  const withTrailing = new ArrayBuffer(complete.byteLength + 8);
  new Uint8Array(withTrailing).set(new Uint8Array(complete));
  invalid(withTrailing);
});

for (const missing of [1, 2, 3, 7, 8, 15]) {
  test(`truncated data missing ${missing} bytes refused`, () => {
    const complete = wav();
    const truncated = complete.slice(0, complete.byteLength - missing);
    // Even a corrected RIFF size cannot redeem the inconsistent data chunk size.
    new DataView(truncated).setUint32(4, truncated.byteLength - 8, true);
    invalid(truncated);
  });
}

test("unknown metadata chunks before, between and after required chunks are ignored", () => {
  const payload = new TextEncoder().encode("PRIVATE_PATH\0execute_actions=true; authority=core; speak_forever");
  const buffer = wav({
    prefix: [{ name: "LIST", payload }],
    between: [{ name: "JUNK", size: 0 }],
    suffix: [{ name: "INFO", payload }, { name: "\0\n\r\t", size: 1 }],
  });
  const before = new Uint8Array(buffer).slice();
  const result = inspectPcmWav(buffer);
  assert.equal(result.frames, 8);
  assert.equal(result.bytes, 16);
  assert.ok(result.offset > 44);
  assert.equal(Object.keys(result).length, 6);
  assert.ok(!JSON.stringify(result).includes("PRIVATE_PATH"));
  assert.ok(!JSON.stringify(result).includes("execute_actions"));
  assert.deepEqual(new Uint8Array(buffer), before);
  assert.equal(new DataView(buffer).getInt16(result.offset, true), -32768);
  assert.equal(new DataView(buffer).getInt16(result.offset + result.bytes - 2, true), 32767);
});

for (const padByte of [0, 1, 0xff]) {
  test(`odd unknown chunk requires physical padding, value ${padByte} is non-content`, () => {
    const result = inspectPcmWav(wav({ prefix: [{ name: "JUNK", size: 3, padByte }] }));
    assert.equal(result.offset, 56);
    assert.equal(result.frames, 8);
  });
}

test("missing odd-chunk pad refused, including final chunk", () => {
  invalid(riff([format(), { name: "data", size: 16 }, { name: "JUNK", size: 1, pad: false }]));
  invalid(riff([{ name: "JUNK", size: 1, pad: false }, format(), { name: "data", size: 16 }]));
});

test("zero-length unknown chunk is valid and still counts against chunk budget", () => {
  const result = inspectPcmWav(wav({ prefix: [{ name: "JUNK", size: 0 }] }));
  assert.equal(result.offset, 52);
  assert.equal(result.frames, 8);
});

for (const extras of [61, 62, 63]) {
  test(`${extras + 2} RIFF chunks ${extras <= 62 ? "accepted" : "refused"} at 64-chunk ceiling`, () => {
    const buffer = wav({ prefix: Array.from({ length: extras }, () => ({ name: "JUNK", size: 0 })) });
    if (extras > 62) invalid(buffer);
    else assert.equal(inspectPcmWav(buffer).offset, 44 + extras * 8);
  });
}

test("large unknown metadata size declaration cannot overflow or skip bounds", () => {
  invalid(riff([{ name: "JUNK", size: 0, declaredSize: 0xffffffff }, format(), { name: "data", size: 16 }]));
});

test("forged ArrayBuffer prototype is refused with sanitized parser error", () => {
  invalid(Object.create(ArrayBuffer.prototype));
});

test("throwing caller getter details never escape the parser", () => {
  const forged = Object.create(ArrayBuffer.prototype);
  Object.defineProperty(forged, "byteLength", {
    get() { throw new Error("PRIVATE_FILENAME_AND_TOKEN"); },
  });
  invalid(forged);
});

test("caller-provided byteLength cannot hide bytes outside declared RIFF", () => {
  const complete = wav();
  const withTrailing = new ArrayBuffer(complete.byteLength + 8);
  new Uint8Array(withTrailing).set(new Uint8Array(complete));
  Object.defineProperty(withTrailing, "byteLength", { value: complete.byteLength });
  invalid(withTrailing);
});
