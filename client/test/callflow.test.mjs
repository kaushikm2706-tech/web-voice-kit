// Tests the call conversation logic with fake speak/listen. Run: npm run test   (Node 22: loads the .ts file directly)
import assert from "node:assert";
import { runCall } from "../src/callFlow.ts";

// A fake "server": same rules as the Python endpoints, just scripted per utterance.
function scenario(utterances, table) {
  const said = [];
  const queue = [...utterances];
  const deps = {
    say: async (t) => { said.push(t); },
    listen: async () => (queue.length ? queue.shift() : null),
    turn: async (text, known) => table.turn(text, known),
    confirm: async (text) => table.confirm(text),
    log: () => {},
  };
  return { deps, said, left: () => queue.length };
}
const full = (amount, day, date) => ({ amount, day, date, prompt: `I heard ${amount} rupees on ${date}. Is that right?`, needsClarification: false, summary: `${amount} rupees on ${date}` });
const askDay = (amount) => ({ amount, day: null, date: null, prompt: `I heard ${amount} rupees. On which day will you pay?`, needsClarification: true, summary: null });

(async () => {
  let r;
  // 1) happy path
  let s = scenario(["A", "yes"], { turn: async () => full(2500, { k: "weekday" }, "2026-10-30"), confirm: async () => ({ intent: "yes", amount: null, day: null }) });
  r = await runCall(s.deps);
  assert.equal(r.status, "confirmed"); assert.equal(r.amount, 2500); assert.equal(r.date, "2026-10-30");
  console.log("PASS happy path: confirmed");

  // 2) day missing -> agent asks for the day -> then confirms
  const turns2 = [askDay(750), full(750, { k: "weekday" }, "2026-10-30")];
  s = scenario(["amount only", "friday", "yes"], { turn: async () => turns2.shift(), confirm: async () => ({ intent: "yes", amount: null, day: null }) });
  r = await runCall(s.deps);
  assert.equal(r.status, "confirmed"); assert.ok(s.said.some((x) => x.includes("On which day")));
  console.log("PASS missing day: agent asked, then confirmed");

  // 3) "no" with a correction -> new read-back -> yes
  const turns3 = [full(2500, { k: "a" }, "2026-10-30"), full(3000, { k: "a" }, "2026-10-30")];
  s = scenario(["first", "no 3000", "yes"], { turn: async () => turns3.shift(), confirm: async (t) => (t === "no 3000" ? { intent: "no", amount: 3000, day: null } : { intent: "yes", amount: null, day: null }) });
  r = await runCall(s.deps);
  assert.equal(r.status, "confirmed"); assert.equal(r.amount, 3000);
  console.log("PASS no + correction: corrected amount confirmed");

  // 4) plain "no" with nothing new -> start over (state cleared), then succeed
  const turns4 = [full(2500, { k: "a" }, "2026-10-30"), full(2500, { k: "a" }, "2026-10-30"), full(1000, { k: "b" }, "2026-10-28")];
  s = scenario(["first", "no", "again", "yes"], { turn: async () => turns4.shift(), confirm: async (t) => (t === "no" ? { intent: "no", amount: null, day: null } : { intent: "yes", amount: null, day: null }) });
  r = await runCall(s.deps);
  assert.equal(r.status, "confirmed"); assert.equal(r.amount, 1000); assert.ok(s.said.some((x) => x.includes("start again")));
  console.log("PASS plain no: restarted and confirmed");

  // 5) silence twice at the start -> gives up, never confirms
  s = scenario([], { turn: async () => { throw new Error("must not be called"); }, confirm: async () => { throw new Error("must not be called"); } });
  r = await runCall(s.deps);
  assert.equal(r.status, "gave_up");
  console.log("PASS silence: gives up politely");

  // 6) unclear answers three times -> gives up, does NOT assume yes
  s = scenario(["A", "hmm", "hmm", "hmm"], { turn: async () => full(2500, { k: "a" }, "2026-10-30"), confirm: async () => ({ intent: "unclear", amount: null, day: null }) });
  r = await runCall(s.deps);
  assert.equal(r.status, "gave_up");
  console.log("PASS unclear x3: never assumes yes");

  // 7) silence after the read-back must NOT count as yes
  s = scenario(["A"], { turn: async () => full(2500, { k: "a" }, "2026-10-30"), confirm: async () => { throw new Error("must not be called"); } });
  r = await runCall(s.deps);
  assert.equal(r.status, "gave_up");
  console.log("PASS silence after read-back is not consent");

  console.log("ALL PASS");
})().catch((e) => { console.error("FAIL", e); process.exit(1); });
