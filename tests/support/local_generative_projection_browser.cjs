// Opt-in proof harness only: owned loopback fixture and an ephemeral browser profile.
// Caller supplies trusted installed test dependencies; never a production MCP/Core API.
const { isAbsolute } = require("node:path");
const { createHash } = require("node:crypto");
const assert = require("node:assert/strict");
if (process.argv.slice(2).length !== 1 || process.argv[2] !== "--authorized") {
  process.stderr.write("projection_browser_authorization_required\n"); process.exit(2);
}
const target = process.env.JARVIS_PROJECTION_TEST_URL;
const secret = process.env.JARVIS_PROJECTION_TEST_SECRET;
const dependency = process.env.JARVIS_PROJECTION_TEST_PACKAGE;
const executable = process.env.JARVIS_PROJECTION_TEST_BROWSER;
if (!/^http:\/\/127\.0\.0\.1:[1-9][0-9]{0,4}\/$/.test(target ?? "") ||
    Number(new URL(target).port) > 65535 || !/^[0-9a-f]{64}$/.test(secret ?? "") ||
    !dependency || !isAbsolute(dependency) || !executable || !isAbsolute(executable)) {
  process.stderr.write("invalid_projection_browser_options\n"); process.exit(2);
}
const { chromium } = require(dependency);
(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: executable });
  try {
    const context = await browser.newContext({ viewport: { width: 1040, height: 900 } });
    const page = await context.newPage(); const requests = [], errors = [];
    page.on("request", (request) => requests.push({ method: request.method(), path: new URL(request.url()).pathname }));
    page.on("pageerror", (error) => errors.push(error.name));
    await page.goto(target, { waitUntil: "networkidle", timeout: 15000 });
    await page.waitForFunction(() => !document.getElementById("live-secret").disabled);
    await page.locator("#live-secret").fill(secret);
    await page.locator("#live-pair").click();
    await page.waitForFunction(() => !document.getElementById("live-send").disabled);
    const query = "Compare os relatórios de documentação e observabilidade do piloto.";
    await page.locator("#live-query").fill(query);
    await page.locator("#live-generative-consent").check(); await page.locator("#live-send").click();
    await page.locator("#live-projection").waitFor({ state: "visible", timeout: 30000 });
    const proof = await page.evaluate(async () => ({
      final: document.getElementById("live-final").textContent,
      query: document.getElementById("live-result-query").textContent,
      analysis: document.getElementById("live-projection-analysis").textContent,
      citations: document.getElementById("live-projection-citations").textContent,
      origin: document.getElementById("live-projection-origin").textContent,
      ticket: document.getElementById("live-ticket").textContent.slice(8),
      session: (await (await fetch("/api/session", { headers: { "X-Jarvis-Client": "local-web-v1" } })).json()).session_ref,
      consent: document.getElementById("live-generative-consent").checked,
    }));
    assert.equal(proof.query, query); assert.equal(proof.consent, false);
    proof.finalSha256 = createHash("sha256").update(proof.final, "utf8").digest("hex");
    proof.finalCharacters = Array.from(proof.final).length;
    assert.match(proof.origin, /injetado de teste/); assert.match(proof.citations, /input:sha256:/);
    assert.equal(requests.filter((r) => r.method === "POST" && r.path === "/api/generative-analysis").length, 1);
    await page.reload({ waitUntil: "networkidle" }); await page.locator("#live-recover").click();
    await page.locator("#live-projection").waitFor({ state: "visible" });
    assert.equal(await page.locator("#live-final").textContent(), proof.final);
    assert.equal(await page.locator("#live-projection-analysis").textContent(), proof.analysis);
    await page.setViewportSize({ width: 390, height: 844 });
    proof.mobile = await page.evaluate(() => ({
      overflow: document.documentElement.scrollWidth > innerWidth,
      shortButtons: Array.from(document.querySelectorAll("button")).filter((n) => !n.hidden && n.getBoundingClientRect().height < 44).length,
      innerScroll: Array.from(document.querySelectorAll("pre")).some((n) => n.scrollHeight > n.clientHeight && ["auto", "scroll"].includes(getComputedStyle(n).overflowY)),
    }));
    assert.deepEqual(proof.mobile, { overflow: false, shortButtons: 0, innerScroll: false });
    if (process.env.JARVIS_PROJECTION_TEST_SCREENSHOT) await page.screenshot({ path: process.env.JARVIS_PROJECTION_TEST_SCREENSHOT, fullPage: true });
    await page.locator("#live-query").fill(query); await page.locator("#live-send").click();
    await page.waitForFunction(() => document.getElementById("live-notice").textContent.startsWith("Resposta final recebida"));
    assert.equal(await page.locator("#live-projection").isVisible(), false);
    assert.match(await page.locator("#live-metadata").textContent(), /generativo desativado/);
    await page.locator("#live-disconnect").click();
    assert.equal(await page.locator("#live-final").textContent(), "");
    assert.equal(await page.locator("#live-projection-analysis").textContent(), "");
    assert.equal(requests.filter((r) => r.method === "POST" && r.path === "/api/generative-analysis").length, 1);
    assert.deepEqual(errors, []); proof.pageErrors = errors;
    process.stdout.write(JSON.stringify(proof) + "\n");
  } finally { await browser.close(); }
})().catch(() => { process.stderr.write("projection_browser_proof_failed\n"); process.exitCode = 2; });
