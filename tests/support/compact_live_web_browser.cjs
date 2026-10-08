// Explicit proof only: owned loopback Core fixture, injected transport, ephemeral browser.
// Trusted test dependencies are caller supplied, never a runtime or authority API.
const { isAbsolute } = require("node:path");
const { createHash } = require("node:crypto");
const assert = require("node:assert/strict");
if (process.argv.slice(2).length !== 1 || process.argv[2] !== "--authorized") {
  process.stderr.write("compact_browser_authorization_required\n"); process.exit(2);
}
const target = process.env.JARVIS_PROJECTION_TEST_URL;
const secret = process.env.JARVIS_PROJECTION_TEST_SECRET;
const dependency = process.env.JARVIS_PROJECTION_TEST_PACKAGE;
const executable = process.env.JARVIS_PROJECTION_TEST_BROWSER;
const screenshot = process.env.JARVIS_PROJECTION_TEST_SCREENSHOT;
let valid = false;
try {
  valid = /^http:\/\/127\.0\.0\.1:[1-9][0-9]{0,4}\/$/.test(target ?? "") &&
    Number(new URL(target).port) <= 65535 && /^[0-9a-f]{64}$/.test(secret ?? "") &&
    typeof dependency === "string" && isAbsolute(dependency) &&
    typeof executable === "string" && isAbsolute(executable) &&
    (screenshot === undefined || isAbsolute(screenshot));
} catch { /* Invalid URL/options must be refused before loading external test dependencies. */ }
if (!valid) { process.stderr.write("invalid_compact_browser_options\n"); process.exit(2); }
const { chromium } = require(dependency);
let proofPhase = "setup";
const disclosureOpen = (page, id, expected) => page.waitForFunction(
  ({ id, expected }) => document.getElementById(id).open === expected, { id, expected });
async function geometry(page) {
  await page.evaluate(() => scrollTo(0, 0));
  return page.evaluate(() => {
    const box = (id) => {
      const rect = document.getElementById(id).getBoundingClientRect();
      return { top: rect.top + scrollY, bottom: rect.bottom + scrollY, height: rect.height };
    };
    const visible = (n) => n.getClientRects().length > 0;
    return { viewport: { width: innerWidth, height: innerHeight },
      query: box("live-query"), consent: box("live-generative-consent"), send: box("live-send"),
      operableBottom: Math.max(...["live-query", "live-generative-consent", "live-send"].map((id) => box(id).bottom)),
      overflow: document.documentElement.scrollWidth > innerWidth,
      shortControls: [...document.querySelectorAll("button, summary, label.consent")].filter((n) =>
        visible(n) && n.getBoundingClientRect().height < 44).length,
      innerScroll: [...document.querySelectorAll("main, section, pre, details")].some((n) =>
        visible(n) && n.scrollHeight > n.clientHeight && ["auto", "scroll"].includes(getComputedStyle(n).overflowY)),
    };
  });
}
(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: executable });
  try {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await context.newPage(); const requests = [], errors = [];
    page.on("request", (r) => requests.push({ method: r.method(), path: new URL(r.url()).pathname }));
    page.on("pageerror", (e) => errors.push(e.name));
    await page.goto(target, { waitUntil: "networkidle", timeout: 15000 });
    await page.waitForFunction(() => !document.getElementById("live-secret").disabled);
    await disclosureOpen(page, "live-pairing-details", true);
    await page.locator("#live-secret").fill(secret); await page.locator("#live-pair").click();
    await page.waitForFunction(() => !document.getElementById("live-send").disabled);
    await disclosureOpen(page, "live-pairing-details", false);
    assert.equal(await page.locator("#live-shell").getAttribute("data-paired"), "true");
    assert.equal(await page.evaluate(() => {
      const details = document.getElementById("live-pairing-details");
      return details.contains(document.activeElement) && document.activeElement.id !== "live-pairing-summary";
    }), false);
    const proof = { mobile: await geometry(page), baselineSendBottom: 1670.625 };
    proof.pairedFocus = await page.evaluate(() => document.activeElement.id);
    assert.equal(proof.pairedFocus, "live-query");
    proofPhase = "mobile_geometry";
    assert.equal(proof.mobile.overflow, false); assert.equal(proof.mobile.shortControls, 0);
    assert.equal(proof.mobile.innerScroll, false);
    assert.ok(proof.mobile.operableBottom <= 2 * 844);
    assert.ok(proof.mobile.send.bottom < proof.baselineSendBottom - 200);
    proofPhase = "pairing_keyboard";
    await page.locator("#live-pairing-summary").focus(); await page.keyboard.press("Enter");
    await disclosureOpen(page, "live-pairing-details", true);
    await page.locator("#live-refresh").click();
    await page.waitForFunction(() => !document.getElementById("live-send").disabled);
    await disclosureOpen(page, "live-pairing-details", true); // Same session must not reset manual choice.
    await page.locator("#live-pairing-summary").focus(); await page.keyboard.press("Space");
    await disclosureOpen(page, "live-pairing-details", false);
    await page.keyboard.press("Tab");
    assert.equal(await page.evaluate(() => document.activeElement.id), "live-refresh");
    await page.keyboard.press("Tab");
    assert.equal(await page.evaluate(() => document.activeElement.id), "live-disconnect");
    const query = "Compare os relatórios de documentação e observabilidade do piloto.";
    proofPhase = "generative_result";
    await page.locator("#live-query").fill(query); await page.locator("#live-generative-consent").check();
    await page.locator("#live-send").click();
    await page.locator("#live-projection").waitFor({ state: "visible", timeout: 30000 });
    await disclosureOpen(page, "live-canonical-details", false);
    Object.assign(proof, await page.evaluate(async () => ({
      final: document.getElementById("live-final").textContent,
      query: document.getElementById("live-result-query").textContent,
      analysis: document.getElementById("live-projection-analysis").textContent,
      ticket: document.getElementById("live-ticket").textContent.slice(8),
      session: (await (await fetch("/api/session", { headers: { "X-Jarvis-Client": "local-web-v1" } })).json()).session_ref,
      consent: document.getElementById("live-generative-consent").checked,
    })));
    assert.equal(proof.query, query); assert.equal(proof.consent, false);
    proof.finalSha256 = createHash("sha256").update(proof.final, "utf8").digest("hex");
    proof.finalCharacters = Array.from(proof.final).length;
    proofPhase = "canonical_keyboard_recovery";
    await page.locator("#live-canonical-summary").focus(); await page.keyboard.press("Enter");
    await disclosureOpen(page, "live-canonical-details", true);
    assert.equal(await page.locator("#live-final").isVisible(), true);
    assert.equal(await page.locator("#live-final").textContent(), proof.final);
    assert.notEqual(await page.locator("#live-canonical-summary").evaluate((n) => getComputedStyle(n).outlineStyle), "none");
    await page.locator("#live-recover").click();
    await page.locator("#live-projection").waitFor({ state: "visible" });
    await disclosureOpen(page, "live-canonical-details", true); // Manual open survives same-result recovery.
    assert.equal(await page.locator("#live-final").textContent(), proof.final);
    await page.locator("#live-canonical-summary").focus(); await page.keyboard.press("Space");
    await disclosureOpen(page, "live-canonical-details", false);
    await page.locator("#live-recover").click();
    await page.locator("#live-projection").waitFor({ state: "visible" });
    await disclosureOpen(page, "live-canonical-details", false);
    proofPhase = "viewports";
    await page.setViewportSize({ width: 390, height: 450 });
    proof.reducedViewport = await geometry(page);
    assert.equal(proof.reducedViewport.overflow, false); assert.equal(proof.reducedViewport.innerScroll, false);
    assert.equal(proof.reducedViewport.shortControls, 0);
    await page.locator("#live-query").focus();
    assert.equal(await page.evaluate(() => document.activeElement.id), "live-query");
    await page.setViewportSize({ width: 1040, height: 900 });
    proof.desktop = await geometry(page);
    assert.equal(proof.desktop.overflow, false); assert.equal(proof.desktop.innerScroll, false);
    assert.equal(proof.desktop.shortControls, 0);
    await page.setViewportSize({ width: 390, height: 844 });
    if (screenshot) { await page.evaluate(() => scrollTo(0, 0)); await page.screenshot({ path: screenshot, fullPage: true }); }
    proofPhase = "reload_recovery";
    await page.reload({ waitUntil: "networkidle" }); await page.locator("#live-recover").click();
    await page.locator("#live-projection").waitFor({ state: "visible" });
    await disclosureOpen(page, "live-canonical-details", false);
    assert.equal(await page.locator("#live-final").textContent(), proof.final);
    assert.equal(await page.locator("#live-projection-analysis").textContent(), proof.analysis);
    // Synthetic response corruption only on GET: parser failure must leave raw text open.
    proofPhase = "parser_failure";
    let refusedFinal;
    await page.route("**/api/results/*", async (route) => {
      const response = await route.fetch(); const envelope = await response.json();
      if (envelope.result?.generative_status === "accepted") {
        envelope.result.response_text += "\nnot a canonical terminal block";
        refusedFinal = envelope.result.response_text;
      }
      // Modified JSON has a different UTF-8 size. Do not reuse its old wire length.
      const headers = { ...response.headers() };
      delete headers["content-length"];
      await route.fulfill({ response, headers, json: envelope });
    });
    await page.locator("#live-recover").click();
    await page.waitForFunction(() => document.getElementById("live-notice").textContent.startsWith("Resposta final recebida"));
    await disclosureOpen(page, "live-canonical-details", true);
    assert.equal(await page.locator("#live-final").textContent(), refusedFinal);
    assert.equal(await page.locator("#live-projection").isVisible(), false);
    await page.unroute("**/api/results/*");
    proofPhase = "native_fallback";
    await page.locator("#live-query").fill(query); await page.locator("#live-send").click();
    await page.waitForFunction(() => document.getElementById("live-notice").textContent.startsWith("Resposta final recebida"));
    assert.equal(await page.locator("#live-projection").isVisible(), false);
    await disclosureOpen(page, "live-canonical-details", true);
    assert.equal(await page.locator("#live-final").isVisible(), true);
    assert.match(await page.locator("#live-metadata").textContent(), /generativo desativado/);
    proofPhase = "disconnect";
    await page.locator("#live-disconnect").click();
    await disclosureOpen(page, "live-pairing-details", true);
    await disclosureOpen(page, "live-canonical-details", true);
    assert.equal(await page.locator("#live-final").textContent(), "");
    assert.equal(await page.locator("#live-shell").getAttribute("data-paired"), "false");
    assert.equal(requests.filter((r) => r.method === "POST" && r.path === "/api/generative-analysis").length, 1);
    assert.equal(requests.filter((r) => r.method === "POST" && r.path === "/api/analysis").length, 1);
    assert.deepEqual(errors, []); proof.pageErrors = errors;
    proof.sendBottomReduction = proof.baselineSendBottom - proof.mobile.send.bottom;
    process.stdout.write(JSON.stringify(proof) + "\n");
  } finally { await browser.close(); }
})().catch(() => { process.stderr.write("compact_browser_proof_failed:" + proofPhase + "\n"); process.exitCode = 2; });
