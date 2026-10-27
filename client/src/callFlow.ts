// web-voice-kit example (UNOFFICIAL, not affiliated with Gnani AI)
//
// The conversation logic of the payment-promise call, with NO browser or network code inside,
// so it can be tested with fake speak/listen functions (see test/callflow.test.cjs).
//
//   agent: "When will you pay, and how much?"   caller: (Tanglish)   agent: reads back amount + date
//   caller: yes -> done.  no (+ maybe a correction) -> fix and read back again.  unclear/silence -> ask again.

export type Day = Record<string, unknown> | null;

export interface TurnResult {
  amount: number | null;
  day: Day;
  date: string | null; // YYYY-MM-DD
  prompt: string; // what the agent says next (a question, or the read-back)
  needsClarification: boolean;
  summary: string | null;
}

export interface ConfirmResult {
  intent: "yes" | "no" | "unclear";
  amount: number | null;
  day: Day;
}

export interface CallDeps {
  say(text: string): Promise<void>;
  /** Resolves with what the caller said, or null for silence / timeout / error. */
  listen(): Promise<string | null>;
  turn(text: string, known: { amount: number | null; day: Day }): Promise<TurnResult>;
  confirm(text: string): Promise<ConfirmResult>;
  log(who: "agent" | "caller", text: string): void;
}

export type Outcome =
  | { status: "confirmed"; amount: number; date: string; summary: string }
  | { status: "gave_up"; reason: string };

export const GREETING =
  "Hello. This is a demo payment promise agent. How much will you pay, and on which day?";
const ASK_AGAIN = "How much will you pay, and on which day?";
const MAX_STEPS = 12;

export async function runCall(deps: CallDeps): Promise<Outcome> {
  const speak = async (text: string) => {
    deps.log("agent", text);
    await deps.say(text);
  };
  const hear = async (): Promise<string | null> => {
    const heard = await deps.listen();
    if (heard !== null) deps.log("caller", heard);
    return heard;
  };

  let t: TurnResult | null = null;
  let silence = 0;
  let unclear = 0;
  await speak(GREETING);

  for (let step = 0; step < MAX_STEPS; step++) {
    // 1) We still need the amount and/or the day.
    if (t === null || t.needsClarification) {
      const heard = await hear();
      if (heard === null) {
        if (++silence >= 2) return { status: "gave_up", reason: "I could not hear anything." };
        await speak("Sorry, I did not hear you. " + (t ? t.prompt : ASK_AGAIN));
        continue;
      }
      t = await deps.turn(heard, { amount: t?.amount ?? null, day: t?.day ?? null });
      await speak(t.prompt); // a question, or the read-back "Is that right?"
      if (t.needsClarification) continue;
    }

    // 2) Everything is known and the read-back was just spoken: wait for yes / no.
    const reply = await hear();
    if (reply === null) {
      if (++silence >= 2) return { status: "gave_up", reason: "No answer to the read-back." };
      await speak("Sorry, I did not hear you. " + t.prompt);
      continue;
    }
    const c = await deps.confirm(reply);
    if (c.intent === "yes") {
      const done = t.summary ?? "";
      await speak(`Thank you. I have noted ${done}. This is only a demo, no payment was made.`);
      return { status: "confirmed", amount: t.amount as number, date: t.date as string, summary: done };
    }
    if (c.intent === "unclear") {
      if (++unclear >= 3) return { status: "gave_up", reason: "I could not tell yes from no." };
      await speak("Sorry, please say yes or no. " + t.prompt);
      continue;
    }
    // "no": did the caller also give a correction?
    const t2 = await deps.turn(reply, { amount: t.amount, day: t.day });
    const changed = t2.amount !== t.amount || JSON.stringify(t2.day) !== JSON.stringify(t.day);
    if (!changed) {
      t = { amount: null, day: null, date: null, prompt: ASK_AGAIN, needsClarification: true, summary: null };
      await speak("Sorry about that. Let us start again. " + ASK_AGAIN);
      continue;
    }
    t = t2;
    await speak(t.prompt); // new read-back, or a question if the correction left something missing
  }
  return { status: "gave_up", reason: "The call went on too long." };
}
