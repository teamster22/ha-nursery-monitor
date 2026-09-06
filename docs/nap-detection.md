# Nap detection

How the state machine decides whether she's asleep, and the measurements it rests
on. Dates are generalized; the numbers are real.

> Read [../DISCLAIMER.md](../DISCLAIMER.md) first.


**Status:** design settled, nothing built. Grounded in real history (3 days, pulled 2026‑07‑14) plus my answers.
**Rev 2** — restructured around the night-bottle case, which turned out to simplify everything.
Companions: `Nursery_Nap_Sensor_Brief.md`, `Nursery_Nap_Build_Guide.md`.

---

## 0. The headline

**Two entities do essentially all the work:**

| | |
|---|---|
| `binary_sensor.nursery_door_open` | is the room sealed? |
| `binary_sensor.nursery_presence_sensor` | is an adult in there? |

Everything else — lights, illuminance, white noise, time of day — is corroboration or veto. None of it is load-bearing.

That's a much smaller system than the brief imagined, and it's *because* of the night-bottle case, not in spite of it.

---

## 1. What the data says

### ① Door closed + dark = sleep window. Every time.

| | Morning | Afternoon | Night |
|---|---|---|---|
| Sat a July night | 09:40 → 11:26 | 14:33 → 16:26 | 19:35 → 07:38 |
| Sun a July night | 09:47 → 11:55 | 14:37 → 16:30 | 19:35 → 07:23 |
| Mon a July night | 09:38 → 11:47 | 14:24 → 16:27 | 19:27 → 06:46 |
| Tue a July night | 09:04 → … | | |

Across 72 hours the door was **never** closed-and-dark outside these windows. Otherwise it sits open for 2–3 hours at a stretch.

The brief argued door-closed is *permissive* evidence — equally consistent with "napping" and "empty room at 2pm." You've now confirmed what the data implied: **you don't close that door unless she's in there.** So the door-close isn't a passive condition, it's the artifact of a deliberate human act. It's a *positive* signal.

### ② A sleeping toddler produces ZERO presence events

Night of one overnight: presence cleared at 19:28:31 and did not fire again until **06:46:29 — 11 hours 18 minutes of silence**, with a sleeping child in the room the whole time.

This is the single most important measurement in the dataset. It means **`nursery_presence_sensor` firing = an adult, essentially always.** The brief's "adults only" claim isn't just vendor spec — it's verified on your instance, over your child, for eleven straight hours.

Which makes presence a clean, trustworthy trigger. And that is what makes the next section work.

### ③ The night bottle is fully visible — and it's in the dark

Sun a July night, 04:18:

```
04:18:05.4  presence  ON      ← adult enters
04:18:05.7  door      OPEN
04:23:05.7  door      CLOSED  ← adult pulls it shut behind them, still inside
04:26:09.8  presence  OFF     ← adult leaves
            lights    never turn on   ← the whole feed happens in the dark
```

An 8-minute visit, 3 minutes of it with the door already closed. Exactly the scenario you described. **It is completely detectable** — and notably, *not* via the lights, because they never come on.

### ④ ⚠️ Anomaly: presence fired with the door shut

Sat a July night, **21:22:35 → 21:25:09** — presence ON for 2m34s. The door was closed from 19:35:59 straight through to 04:18:05. Lights off. Nobody opened that door.

Two possible explanations:

- **mmWave bleed-through.** 60 GHz radar sees through hollow-core doors and drywall. It may have caught someone in the hall. This is a well-known mmWave failure mode.
- **The door sensor missed an event.** Less likely — it looks reliable everywhere else.

**This matters a lot.** A naive rule of "presence ⇒ she's awake" would have flipped her out of `asleep` for 2.5 minutes at 21:22 on a night when nothing happened. That's a false wake, at bedtime, in exactly the window where you'd most want to trust the sensor.

**Fix (see §2): the door-open *event* is the entry trigger, not presence.** Doors don't open themselves. Presence is used to decide when the visit *ends*, not when it starts. That single choice makes the machine immune to radar bleed-through.

I can't fully resolve which explanation is right from 3 days. Shadow mode will.

### ⑤ The Sonos is inert

`idle` or `unavailable` for all 72 hours. Never played once. You said it's not a sleep signal; the data says it contributes *nothing*. Keep it only as a hard veto if it ever plays.

*(Aside: it's flapping `unavailable`↔`idle` every ~10 min through a July night, despite the DHCP fix logged that day. Fleet-health issue, not a nap issue — but worth a look.)*

### ⑥ Two corrections to the brief

- **The wall remote does not have 4 free buttons.** All four *taps* are bound (20% / 100% / toggle lamp / off), and both right-hand *holds* are bound to dimming. But **`hold_top_left` and `hold_bottom_left` are empty.** Two free holds — enough.
- **`automation.nursery_dim_presence_light` does not exist.** Stale reference in the brief.

---

## 2. The state machine

### The reframe

> **The nursery is a one-way box.** A toddler in a crib behind a closed door cannot change her own occupancy. It only changes when **an adult crosses the threshold.**

So don't sense the child. **Detect and bound adult visits.** The door-open event opens a visit; presence-clear closes it.

### The unification — this is the good bit

Your night-bottle case looked like it needed special handling. It doesn't. **A re-settle after a 4am bottle has the identical signature to a bedtime put-down:**

```
presence clears  +  door closed  +  dark  →  sustained  →  she's down
```

It makes no difference whether the visit began from `awake` (bedtime) or from `asleep` (night waking). **There is exactly one transition that means "she's now down," and it's the same one every time.** Bedtime, nap-time, and 4am all collapse into one rule.

### States

| State | Meaning | Confidence |
|---|---|---|
| `unknown` | after a restart — **do not guess** | 0 |
| `awake` | door open, sustained | 0 |
| `tending` | a visit is open — adult in the room, child awake or being settled | ~5 |
| `settling` | visit closed, door shut, dark — timer running | 40–60 |
| `asleep` | settled and stable | 80 (95 if declared) |
| ~~`out`~~ | ~~household away~~ — **REJECTED, never built. See §6.** A sitter puts her down exactly the same way; this veto would wake her. | — |

`tending` covers **bedtime put-downs, nap put-downs, night bottles, and morning pickups alike.** It's one state because they're one thing: an adult is in the room and the child is not reliably asleep. That is exactly the point-of-truth you asked for.

### Transitions

```
  ANY ──── door OPEN (event) ──────────────► tending
                                               │
                          ┌────────────────────┤
                          │                    │
      door open >2 min    │                    │  door CLOSED
      (+ lights on)       │                    │  AND presence clear ≥90 s
                          ▼                    ▼
                        awake              settling
                                               │
                                               │  stable for T (tune: 5–10 min)
                                               ▼
                                            asleep
                                               │
                                    door OPEN ─┘ (→ tending)
```

Plus, orthogonally:

- **wall-remote hold** → declare `asleep` / `awake` directly, confidence 95. Overrides everything.
- **max-duration decay** → confidence sags past a plausible nap length. *(This replaces the rejected household-away veto — see §6.)*
- **max-duration decay** → if `asleep` beyond plausible (see below), decay confidence toward `unknown`.

### Why door-open is the entry trigger, not presence

Because of §1④. Presence can fire through a closed door; **a closed door cannot open itself.** Keying entry on the door event makes the machine structurally immune to mmWave bleed-through, at the cost of missing a visit if the door sensor ever drops an event.

That's the right trade: **a missed 2-minute visit is a much cheaper error than a phantom wake at bedtime.**

Verify it against the real data:

| Event | Machine does | Correct? |
|---|---|---|
| a July night 04:18 night bottle (door opens) | → `tending` → `settling` at 04:27:39 → `asleep` | ✅ |
| a July night 21:22 phantom presence (no door event) | **nothing — stays `asleep`** | ✅ |
| a July night 19:27 bedtime (door closes, presence clears 19:28:31) | → `settling` at 19:30:01 → `asleep` | ✅ |
| a July night 06:46 morning (door opens, stays open) | → `tending` → `awake` at 06:48 | ✅ |

Every transition in three days, handled by four rules.

---

## 3. Confidence

The brief's formula — a weighted sum of current conditions — is **the stateless trap the brief warns about three sections earlier.** It recomputes from scratch and cannot tell "door closed because she was just put down" from "door closed since breakfast." Confidence must be **anchored to the entry event, then decayed:**

```
confidence = base(how we entered)
           × duration_plausibility(elapsed, is_night)
           − vetoes
           + corroborations
```

**Vetoes (hard → 0):** door open >2 min · Sonos playing · illuminance high & sustained. **NOT household-away — see §6.**

**Corroborations (+, small):** illuminance ≈ 0 · white noise on (decaying weight — see §5).

**duration_plausibility** — see §3a. Rebuilt a weekday in July after I pushed back on the caps; the pushback surfaced two real bugs.

---

## 3a. The max-duration decay (rebuilt a weekday in July)

I: *"Some naps may exceed 3 hrs, and some overnight sleeps may exceed 12 hrs."* He was right, and checking it against the real history turned up **three bugs**, one of them nasty.

### The principle I'd got wrong

**The cap marks "implausible," not "typical max."** The decay's job is *fault detection* — catching a stuck state machine, a dropped door event, a dead sensor battery. It is **not** a model of how long she sleeps.

Set the cap near the typical maximum and it fires during ordinary long sleeps — producing low confidence *precisely when she is actually asleep*. That is a **false negative**, and per §6 the false negative is the error that **wakes the child**. Same failure direction as the rejected household-away veto. I'd made the same mistake twice.

### The three bugs

**① The night cap was below the observed maximum.**

| | Observed max | Old cap | |
|---|---|---|---|
| Nap | 2h09m (129 min) | 180 min | tight — 40% headroom |
| Night | **12h03m (723 min)** | **720 min** | **cap sits *below* real data** |

**② The day/night gate read `input_boolean.nighttime` *now*, not at sleep start.** This is the nasty one. That boolean flipped off at **06:16** on a July night while she was still asleep (19:27 → 06:46). The cap snapped 720 → 180 min with 649 minutes already elapsed. **Confidence would have read `0` for the last 30 minutes of a completely normal night's sleep.**

**③ A declared nap (base 95) never decayed at all.** A stale manual override would have sat at 95 forever if the door sensor ever dropped its wake event.

### The fix

- **Night-ness is now fixed at sleep start** (from the hour of `input_datetime.nursery_sleep_started`), never re-evaluated. `nighttime` is no longer referenced.
- **Night = start hour ≥ 17 or < 6.** Deliberately generous. **When unsure, classify as night** — a nap wrongly given the night cap just decays later (harmless); a night wrongly given the nap cap craters confidence during real sleep (wakes her).
- **Linear fade from a plateau to zero**, and it now applies to declarations too.

| | Plateau (full confidence) | Zero at |
|---|---|---|
| **Nap** | **210 min** (3.5 h) | 360 min (6 h) |
| **Night** | **840 min** (14 h) | 1020 min (17 h) |

### Verified against every real sleep in the history

| | Elapsed | Confidence |
|---|---|---|
| Longest observed nap | 129 min | **85** ✅ |
| Longest observed night *(was decaying)* | 723 min | **85** ✅ |
| 4am re-settle *(start hour 4 → night cap)* | 139 min | **85** ✅ |
| 3.5 h nap | 210 min | **85** ✅ headroom |
| 4 h nap | 240 min | 68 |
| 14 h night | 840 min | **85** ✅ headroom |
| **Stuck — 5 h "nap"** | 300 min | 34 |
| **Stuck — 6 h "nap"** | 360 min | **0** |
| **Stuck — 17 h "night"** | 1020 min | **0** |
| **Stale declaration, 6 h** | 360 min | **0** ✅ now decays |

Every genuine sleep in three days of history now sits flat at 85. Every fault collapses to zero in bounded time.

### Was the change necessary? Yes — but the caps were the smaller half

Raising the caps alone would have been a modest tuning tweak. **Bug ②** was the real find, and it would have quietly zeroed confidence at dawn every single morning. It only surfaced because the question forced a replay against real timestamps rather than against my own assumptions.

---

### The honest ceiling

**Cap inferred confidence at ~85. Only a button hold should exceed it.**

So **"mute notifications at ≥90" is not reachable by inference alone.** You press the button, or you wait for the load cells. I'd rather say that than inflate a number until it clears the bar — a confident 92 that's wrong is worse than an honest 80.

---

## 4. ⚠️ The one-nap transition: do NOT build a time-of-day prior

You're stable on two naps and expect the one-nap transition within ~2 months.

**The signal a naive design leans on hardest — time of day — is precisely the one with a known expiry date.** A hard-coded nap window (or a `schedule` helper) will quietly start lying to you in eight weeks, and it will lie in the most annoying possible way: it'll be *mostly* right, so you won't notice immediately.

**The door doesn't care what time it is.** It's an invariant. Lean on it.

Recommendation: **omit the time-of-day prior from v1 entirely.** It buys very little (the door is already near-deterministic) and it's a liability with a scheduled failure date. The only clock-derived input worth keeping is `input_boolean.nighttime` — because *night* is stable even as *nap times* move — and only to switch the duration-plausibility curve, never to gate the state.

When the transition comes, this design needs **zero changes.**

---

## 5. The white-noise machine — hold off

Direct answer to your offer: **don't install it this afternoon. It's not load-bearing, and I don't want it to become load-bearing.**

Reasoning:

- The door + presence pair already carries the signal. White noise adds no *state* the machine doesn't have.
- It doesn't fix the night bottle (presence does).
- It doesn't fix the one-nap transition (the door does).
- **And you've told me it's unreliable in a specific, asymmetric way** — on early (books), off late (forgotten). Adding a known-unreliable input to a system whose primary signal is strong is how you make a good system worse.

If you do add it (it's free and takes 30 minutes), then **hard rule: it may never create or destroy an `asleep` state.** Corroboration only, small weight, decaying with elapsed time. Never a veto. Score the **edges**, not the state:

| Signal | Correct use |
|---|---|
| ON transition | **Precursor** — "a put-down is likely within ~30 min." Raises the prior. Not evidence of sleep. |
| Steady ON | Weak corroboration with a **decaying** weight (the "forgot to turn it off" hypothesis grows over time) |
| OFF transition | Reliable negative *when it fires* — but **lagging**, so never read its absence as evidence |

**Where it would genuinely earn its keep:** as a *separate*, low-stakes trigger to pre-dim the hall lights during wind-down — before the nap sensor commits to anything. That's a nice use. It just isn't this project.

Let shadow mode tell us if it adds anything. My prediction: it won't.

---

## 6. The corner case — and why the household-away veto is REJECTED

I originally proposed a household-away veto: if both `person.parent_a` and `person.parent_b` are `not_home`, force state `out`, confidence 0. **I caught the flaw. The veto is rejected and was never built.** Here's the full reasoning, because it's a good lesson about which direction a guard fails in.

### It fails in the dangerous direction

The babysitter case is real and recurring: both parents out, sitter puts her down, the put-down flow is **completely unchanged** (adult in room → lights off → door closed behind a child in the crib). The sensors see a textbook nap.

The veto would then override that with "nobody's home, she can't be asleep" → confidence 0 → doorbell not suppressed, hall lights not dimmed → **and the automations wake the sleeping child.**

Now look at the two error types:

| | What it costs |
|---|---|
| **False positive** (think she's asleep, she isn't) — what the veto guards against | Lights dim and the doorbell is muted in an empty house. Mildly annoying. **Nobody notices.** |
| **False negative** (think she's awake, she's asleep) — what the veto *causes* | The doorbell rings. **A sleeping child wakes up.** |

The veto trades a **rare, harmless** error for a **recurring, harmful** one. That's backwards. A guard whose failure mode is worse than the thing it guards against is not a guard.

### It's also nearly redundant

The case it's meant to catch is "door closed, she's not in there." But **when she's out with you, the door is open** — you've confirmed you only close it to put her down. So the door signal already handles it. The veto adds almost nothing on the upside while adding a real hazard on the downside.

### What we use instead

**Max-duration decay** (implemented, in `sensor.nursery_nap_confidence`). If `asleep` persists past plausible — 180 min day / 720 min night, gated on `input_boolean.nighttime` — confidence decays rather than sitting at 85 forever.

This is strictly better because it's **generic**: it catches the stuck-state case *and* sensor dropouts, missed door events, and failure modes nobody has thought of yet — without knowing or caring who is home. It also fails in the safe direction (confidence drifts down, so the cautious automations disengage first).

### What still isn't solved

"She's downstairs with a parent and someone shut the nursery door for no reason." Nothing catches that short of the load cells — a closed dark door with no one in it is genuinely indistinguishable from a closed dark door with a sleeping child behind it. **That's the manual override's job**, and it's precisely the gap `binary_sensor.crib_occupied` closes.

> **The general principle, worth keeping:** before adding a guard, ask which direction it fails in and how often. A veto built on "who is home" cannot know about sitters, grandparents, or the other parent's phone dropping off Wi-Fi — and every one of those failures wakes the child.

---

## 7. What this can never do

1. **It cannot tell "asleep" from "awake, standing in the crib, quietly babbling."** Door closed, room dark, no adult has come — every signal reads asleep. **This is the ceiling of the software layer, and it is exactly what `sensor.crib_restlessness` fixes.**
2. It can't detect a wake that resolves itself before an adult goes in.
3. Three days is three days. The regularity is striking; design for re-tuning.

---

## 8. Build order

| # | Step | Notes |
|---|---|---|
| 1 | **Data hygiene** | Remove the dead `binary_sensor.nursery_door_is_open`. Make every automation treat `unavailable` as **unknown**, never as closed/off — this is the most likely source of a phantom nap. |
| 2 | **Smoothed illuminance** | Raw lux swings 400→680 within seconds. Add a `statistics` mean-over-5-min helper (per the project's "prefer smoothed sensors" rule) and use **that**, not `light.nursery_lights` — the light group goes `unavailable` frequently, and the illuminance sensor rides the *same device* as presence, so it's one less integration to fail. |
| 3 | **Ground truth** | Bind `hold_top_left` → "she's down", `hold_bottom_left` → "she's up". *(Baby Buddy was removed a weekday in July — the old `bb_sleep_helper` fire is gone and must not be re-added.)* |
| 4 | **State machine** | `input_select.nursery_state`, `input_datetime.nursery_sleep_started`, `input_number.nursery_confidence` |
| 5 | **Four transition automations** | Per §2 |
| 6 | **Shadow mode, 2 weeks — drives nothing** | Log inferred state + confidence + button truth + all inputs |
| 7 | **Tune, then wire consumers** | |

### Why shadow mode is not optional

- The button stops being a signal and becomes the **training label**.
- You get the real **nap-duration distribution** for the plausibility curve — which you need *twice*, since it'll change at the one-nap transition.
- You can check **calibration**: when it says 80, is she actually asleep ~80% of the time? An uncalibrated confidence score is a vibe, not a probability.
- **It resolves the §1④ anomaly** — two weeks will show whether presence-through-a-closed-door is a recurring radar artifact or a one-off missed door event.
- **It's the same harness you'll need to prove the load cells are better.** Build it now, and the hardware lands in a system that can immediately grade it.

### Consumer thresholds — set by the cost of being wrong

| Consumer | Threshold | Cost of a false positive |
|---|---|---|
| Dim hall lights | ≥ 50 | Trivial |
| Suppress doorbell | ≥ 75 | Miss a delivery |
| Mute notifications | ≥ 90 | Miss something that matters — **button-only, by design** |
