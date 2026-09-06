# The tablet parent unit

A wall-mounted Android tablet running Fully Kiosk Browser, showing one Home
Assistant dashboard view with the nursery camera on it. The goal was Eufy E10
parity: press a button, see the room, instantly.

> Read [../DISCLAIMER.md](../DISCLAIMER.md) first. Short version: not a medical
> device, and an LLM wrote essentially all of the code here. I'm not a software
> engineer, so read the config yourself before you run it.

## The one idea that makes it work

**Dormant is not screen-off.**

Dormant means brightness 0, volume 0, over a **still-playing** video element, with a
black overlay card on top. The stream never stops. The screen never sleeps.

That sounds wasteful and it's the entire point. Android **suspends** WebView media
when the screen sleeps, so a true screen-off means the stream has to be rebuilt on
wake: three to eight seconds of black, then a reconnect. Keeping the video element
alive at brightness 0 makes the wake sub-second, which is the difference between
something that feels like an OEM baby monitor and something that feels like you're
loading a web page while your child cries.

The cost is that the panel may glow faintly, because Android brightness 0 is often
"dimmest" rather than "off." The black overlay card covers that. If your specific
panel visibly glows through it, that's the one reason to reconsider true screen-off.

## The two wake paths

Waking after a **hardware power button** press has to converge on the same end state
as the soft wake. It's allowed to take longer. It is not allowed to end up somewhere
different.

- **Fast path** (already dormant, screen on): set brightness, set volume, drop the
  overlay, start the inactivity timer. Sub-second.
- **Slow path** (screen genuinely off): wait for Fully to report the screen on, settle
  two seconds, press "load start URL" to rebuild the page and re-establish the
  suspended stream, wait for the reload, *then* touch brightness and volume. Eight to
  ten seconds, paid only when needed.

Setting brightness and volume blindly on the slow path gives you a lit screen showing
a frozen or silent feed. It looks awake and it isn't.

### `force_recovery` exists because of a race

If the **user** presses the power button, the screen already reports on by the time
the automation reacts. The script's own check then computes "fast path" and leaves a
suspended stream behind a lit screen. So the hardware-power-button automation passes
`force_recovery: true` to force the slow path. That parameter is not decoration.

## Brightness goes through a helper, never straight to the device

This one cost me a day of thinking the buttons were broken.

The Fully Kiosk brightness number entity **round-trips in 20 to 30 seconds**. The
original steppers read that entity, added 30, and wrote it back. So a second tap
inside that window read the *same stale value* and computed the *same target*. Two
presses moved the screen 30, not 60. And `mode: single` plus a blocking HTTP write
meant extra taps were dropped outright with "Already running." The logbook showed a
single 255 to 225 step from several presses. The control felt dead because it very
nearly was.

The fix: the buttons step `input_number.nursery_monitor_brightness`, which is instant
and always truthful, and one automation with `mode: restart` mirrors that helper to
the hardware. A burst of taps collapses to a single write of the final value.

**Helper is intent, device is reality.** Don't put two writers on a slow entity.

## Fully Kiosk setup

Fully Kiosk Browser PLUS (the paid version). You need the Remote Admin API for Home
Assistant to control it.

| Setting | Value | Why |
|---|---|---|
| Screen timeout | never | dormancy is managed by HA, not Android |
| Keep screen on | yes | same reason |
| Remote administration | on, with a password | this is the HA integration's channel |
| Start URL | your dashboard view URL | |
| Screensaver | off | it fights the overlay |

Add the Fully Kiosk Browser integration in Home Assistant pointing at the tablet's
IP and that admin password.

## Audio paths that will waste your time

**The chime needs an absolute URL.** `fully_kiosk` can't resolve a relative
`/local/...` path, because the tablet is a separate device on your LAN and Home
Assistant's own base URL is `127.0.0.1` as far as it's concerned. A relative path
produces a "file not found" toast **on the tablet** and no error at all in the HA
log. The find-tablet script derives the absolute URL from the tablet's own reported
current page, so it survives an IP change.

**A Lovelace `tap_action`'s `data:` is static config.** Jinja in it is never
rendered. It ships as a literal string and fails validation with an error toast on
the tablet. That's why the volume and brightness arithmetic lives in scripts and the
cards pass a static direction with no numbers.

## Find-my-tablet

Wakes the panel and plays the chime once at full volume for about 15 seconds, then
restores the listening volume. It wakes the screen too, because in a dim room a lit
screen is often what actually finds it.

It was three passes originally. Fifteen seconds is enough to get a bearing, and an
over-long alarm you can't stop is worse than one you re-tap. **If you lengthen it,
add a cancel, not more repeats.**

It deliberately ignores both the volume helper and the acoustic-feedback guard. The
whole point is being findable, and a device muted to 10% can't be found by ear.

## The acoustic feedback loop

If you carry the tablet into the nursery while it's unmuted, the tablet's speaker
feeds the camera's microphone, Frigate re-triggers on the audio, and you have a
self-sustaining alert loop.

`binary_sensor.nursery_adult_present` guards against it: volume goes to 0 whenever
an adult is in the nursery. That sensor is composed (state is `tending`, OR the door
is open, OR presence and person fire together) and it evaluates **false** when its
inputs are unavailable, so a sensor outage wakes with audio working rather than
silently muted. Failing loud beats failing quiet on a baby monitor.

## Android prep

Set the tablet up as a Device Owner with no Google account. It's a wall panel, not a
personal device, and it doesn't need to be logged into anything.

## Original working notes

What follows is the raw build proposal, lightly scrubbed. It's long and it's written
to myself, but it has the reasoning behind most of the decisions above.

---


**Status:** **build in progress — N2, N3, N4, N5 complete.** One NUC edit applied (the `nursery_kiosk` audio stream, §5). `HA_Reference.md` reconciled each phase.
**Device:** Lenovo Tab One (8.7" 1340×800 IPS · MediaTek Helio G85 · 4 GB / 64 GB · Android 14→15 · Wi-Fi 5 · 5,100 mAh · USB-C)
**Target behaviour:** replicate the **Eufy SpaceView E10** parent unit (§3).
**Date:** that month · **Rev 5** — **N1 locked to Device Owner provisioning with no Google account (§8).** Power/volume button behaviour settled (§3.8), and one earlier overclaim about the power menu corrected there.
**Companion:** [nap-detection.md](nap-detection.md).

**Locked decisions:**

| | |
|---|---|
| Behaviour model | **Eufy E10 parity — dormant by default, wakes on qualified cry (§3)** |
| Audio | **Nursery → tablet only. Plays while awake, silent while dormant. NO talkback (§5a)** |
| Screen | **Never truly off — brightness 0 + black overlay, indistinguishable from off (§3.3)** |
| Wake triggers | **Qualified cry, or touch. No walk-up motion — camera + mic permissions both denied** |
| Inactivity timeout | **5 min** |
| Cry qualifier | **5 s sustained** (revised from 10 s after live measurement, §3.6), 6-min tone cooldown |
| Presence suppression | **Yes** — no wake, no tone when an adult is already in the nursery |
| Kiosk app | **Fully Kiosk PLUS — approved** (€7.90) |
| Placement | **Floating device.** Home base = Primary Bedroom bedside, plugged in (§3.7) |
| Area / labels | **New area `Floating Devices`** · labels `baby` + `kiosk` (both approved) |
| Dashboard | **New `nursery-monitor` dashboard, read-only for v1** (§6) |
| Provisioning | **Device Owner, and NO Google account on the device** — the two are interdependent (§8) |
| Hardware buttons | **Volume = nursery audio (free, no config). Power = deep standby, HA follows it** (§3.8) |

---

## 1. The target

An OEM baby monitor does five things without being asked:

1. Shows the crib when there's something to see, and nothing at all when there isn't.
2. Makes noise when she makes noise — **audio is the primary channel**, video is confirmation.
3. Lights up by itself, with an alert tone, when something qualifies.
4. Never shows a menu, a login, an update prompt, or a black screen you can't interpret.
5. Fails loudly. A dead OEM monitor beeps. A dead tablet just looks like a dark nursery — **the most dangerous failure mode in this project**, and §9 is dedicated to it.

Where a "smart home dashboard" instinct conflicts with an "appliance" instinct, the appliance wins.

---

## 3. The behaviour model — Eufy E10 parity

### 3.1 The two states

| | **DORMANT** | **ACTIVE** |
|---|---|---|
| Screen brightness | **0** | day ~100 % · night ~25 % |
| Page content | **full-screen black overlay** | monitor layout (§6) |
| Device volume | **0** | user-set, adjustable |
| WebRTC stream | **connected and playing, silently** | connected and playing, audible |
| Looks/sounds like | **off** | a baby monitor |

**The trick: the stream never stops.** DORMANT is brightness 0 and volume 0 over a live, still-playing video element. Two numbers, both instant.

### 3.2 The transitions

**DORMANT → ACTIVE**

| Trigger | Alert tone? |
|---|---|
| **Qualified cry** — `binary_sensor.nursery_crying_sound` on for **≥ 10 s** | **Yes**, if the 6-min cooldown has expired |
| **Touch anywhere on the black overlay** | No |

No walk-up motion detection (your call) — which means **camera and microphone permissions are both denied at the Android level.** Clean.

**Consequence: the dormant black overlay must itself be a tap target that wakes the panel.** With motion detection gone, touch is the *only* manual wake, and a black overlay that swallows taps would leave you with no way in. This is a small implementation detail with a large failure mode; it's called out again in §6 and in the N5 acceptance criteria.

**ACTIVE → DORMANT**

`timer.nursery_monitor_inactivity` (**5 min**, matching the E10) expires with no cry and no touch. Every qualifying event restarts it. On expiry: volume → 0, brightness → 0, overlay on. A **☾ Sleep now** button drops there immediately.

### 3.3 Why the screen never truly turns off

- **Audio ceasing while dormant is the desired behaviour**, so screen-off's audio-suspension is no longer a bug to work around.
- What remains is worse: **if the media element is ever paused and resumed, the browser's autoplay policy can silently refuse to play unmuted audio again.** A monitor that looks healthy and makes no sound. Never pausing the element removes that entirely — the autoplay-gesture problem becomes once-per-page-load instead of once-per-wake.
- Wake latency: brightness ramp is **sub-second**; cold screen-on plus WebRTC renegotiation is **3–8 s**.

**Verify early:** Android brightness 0 is often "dimmest," not off. The **full-screen black overlay** covers it — a conditional card, *not* a navigation. Navigating away tears down the stream and reintroduces every problem above. If the panel still visibly glows on this unit, that's the moment to reconsider true screen-off, with the audio-resume risk understood.

### 3.4 Qualified cry

| Layer | Setting | Status |
|---|---|---|
| Frigate confidence | `threshold: 0.75` | ✅ live |
| Frigate volume floor | `min_volume: 300` | ✅ live |
| Frigate hold | `max_not_heard: 30` — a pause for breath doesn't end the event | ✅ live |
| **Duration qualifier** | HA trigger **`for: 00:00:05`** — revised down from 10 s after the 07-28 latency measurement (§3.6) | ⬜ build |
| **Alert cooldown** | `timer.nursery_monitor_alert_cooldown`, **6 min** — gates the *tone*, not the wake | ⬜ build |
| **Presence suppression** | No wake, no tone when `binary_sensor.nursery_presence_sensor` is on or `input_select.nursery_state` = `tending` | ⬜ build |

**Tuning:** 10 s is the starting value. Raise `min_volume` first if 3 a.m. false positives appear (per your own config comment); raise the qualifier if real-but-brief noises keep waking the panel. Both are one-line changes.

**Presence suppression does double duty.** Beyond "don't beep at me while I'm standing over the crib," it's also the natural guard against the floating-tablet feedback loop (§3.7) — if the tablet is carried into the nursery, an adult carried it, so presence is on and the panel stays quiet.

### 3.5 The alert tone

**Spec:** two quick beeps → 3 s pause → repeat, **4 cycles, 8 tones total**, ~12–14 s. Attention-grabbing but pleasant.

**Build it as ONE pre-rendered audio file.** Do not implement the pattern as a script looping `fully_kiosk` play-media calls — that puts eight network round-trips and a `delay:` loop between a crying baby and the sound that tells you about it. One file, one call, timing baked in and identical every time.

**✅ CHOSEN that month — "rising bell" (variant A).** Two-note rising bell, **A5 (880 Hz) → E6 (1318.5 Hz)**, sine fundamental plus 2nd/3rd harmonics at 0.35/0.12, exponential decay envelope with a 6 ms squared attack ramp so there is no click. 55 ms between the two notes, 3.0 s between cycles, 4 cycles, **8 tones, 13.14 s total**. Warm and musical rather than harsh — reads as "attention," not "error."

Files live in the project folder at `nursery_monitor/`:
- `nursery_alert_chime.mp3` — 206 KB, 128 kbps mono. **The one to deploy.**
- `nursery_alert_chime.wav` — 1.2 MB, 44.1 kHz 16-bit mono. Fallback if Fully's player dislikes the MP3.
- `chime_generator.py` — the numpy generator. Keep it: re-render with different pitch, spacing, or cycle count in one edit rather than starting over.

**⬜ Deployment is a manual step.** `ha_write_file` is **text-only**, so the connector cannot push a binary MP3 — writing it as text corrupts the file. Upload via the File editor to **`www/nursery_monitor/nursery_alert_chime.mp3`** (same route used for the 8 Flux wallpapers), which serves it at:

```
/local/nursery_monitor/nursery_alert_chime.mp3
```

That URL is what the wake script hands to Fully's play-media call at N1.

Two details:
- **Volume:** set the alert level independently of the listening level, and restore the listening level after. The tone should wake you; nursery audio at that volume would not be pleasant.
- **Stoppable:** touching the screen stops playback (`fully_kiosk` exposes stop-media). If you're already looking at it, the remaining beeps are noise.
- Fires **only** on the cry transition. Never on a touch wake.

Confirmed: **the tone plays on the tablet only. Nothing sounds in the nursery.**

### 3.6 Latency budget — **MEASURED that month, not estimated**

| Stage | Estimated | **Measured** |
|---|---|---|
| Cry begins → `binary_sensor.nursery_crying_sound` on | ~1–3 s | **7–10 s** |
| Duration qualifier (by design) | 10 s | 10 s as planned |
| Frigate → MQTT → HA → automation → Fully REST | <1 s | <1 s |
| Brightness + volume change (stream already live) | <1 s | <1 s |
| **Total, cry to lit-and-audible** | ~12–15 s | **~17–20 s** |

**Recommendation arising from the measurement: drop the qualifier from 10 s to 5 s.** Frigate's detector is already not a hair trigger — it needs 7–10 s of sustained crying just to assert the sensor, which is itself a duration filter. Stacking a 10 s HA qualifier on top double-charges for the same protection and pushes cry-to-wake past 20 s. At 5 s (matching the existing `automation.nursery_baby_crying_critical`) total wake lands at ~12–15 s, which is what the plan promised. Revisit during the N7 bake-in if false wakes appear.

### 3.9 Measured detector behaviour — the two that month tests

Both tests played recorded crying in an empty nursery at crib distance. **This was the first time `binary_sensor.nursery_crying_sound` had ever fired** — before 13:36 on that month its entire history was `unavailable` → `off`.

| | Test 1 | Test 2 |
|---|---|---|
| Audio duration | ≈35 s | ≈15 s |
| Sensor ON | 13:36:54.386 | 13:43:46.846 |
| Sensor OFF | 13:37:24.634 | 13:44:19.981 |
| **ON duration** | **30.25 s** | **33.13 s** |
| Peak RMS | 5,096 (−16.2 dBFS) | 3,689 (−19.0 dBFS) |

**The decisive comparison: audio duration was cut by more than half between the tests, and sensor-ON duration did not change.** Had the sensor tracked the sound, test 2 should have shown ~15 s. It showed 33 s.

**Conclusion — `max_not_heard: 30` holds the sensor through silence.** The sensor stays on ~30 s from onset regardless of when the sound stops. Two consequences:

1. **The `for:` qualifier is safe.** Pauses between sobs will not drop the sensor mid-count, which was the risk that prompted these tests. A real baby crying in bursts will hold the sensor continuously.
2. **A single brief cry produces ~30 s of ON.** The inactivity timer and cooldown logic must assume a 30 s floor on every event, not a duration that reflects the actual crying.

**Instrumentation caveat, recorded honestly:** Frigate's `/api/stats` refreshes `audio_rms` only every ~18 s, so the audio-stop moment can't be pinned closer than ±18 s. The conclusion doesn't depend on it — even taking the latest possible stop time, "tracks the sound" predicts OFF by 13:44:09 against an observed 13:44:20.

**Two incidental findings:**
- `min_volume: 300` is well placed but not marginal — peaks hit 5,096, seventeen times the floor. Raise it first if 3 a.m. false positives appear, per the config's own note.
- **`automation.nursery_baby_crying_critical` fired correctly** at 13:36:59, exactly 5 s after sensor-on. The independent phone-alert channel is proven working.

### 3.7 It's a floating device — what that changes

Home base is the Primary Bedroom bedside, plugged in. But it moves around the house, which changes four things:

1. **Battery becomes a first-class concern.** A live video decode 24/7 is a real drain — expect **roughly 5–8 hours unplugged**, to be measured during bake-in. Mitigations: a **low-battery alert at 20 %** (new automation, §7.3) so it never silently dies mid-float, and an **optional battery-saver mode** — when unplugged *and* dormant, tear the stream down and accept a 3–8 s wake instead of sub-second. Not built by default; §11 leaves it open until bake-in shows whether it's needed.
2. **The smart-plug charge cycle is dropped.** Floating means it naturally discharges and recharges. The battery gets its duty cycle for free — one fewer automation and one fewer smart plug.
3. **Acoustic feedback if it enters the nursery.** Its speaker would feed the camera mic, which feeds Frigate's cry detector, which could self-trigger. Presence suppression (§3.4) covers the common case. **Belt and braces: force volume 0 whenever `binary_sensor.nursery_presence_sensor` is on**, folded into `script.nursery_monitor_wake`.
4. **Networking is fine.** A DHCP reservation is by MAC, so it follows the tablet across the Deco mesh. HA reaches it at a stable IP from any room.

**Consequence for the offline alert (§9.2):** it will fire when you let the battery die on the couch. That's correct behaviour, not a bug — the low-battery warning at 20 % is what makes it predictable rather than annoying.

---

## 3.8 Hardware buttons — power and volume

Goal: the physical buttons should behave like an appliance's, not a tablet's. The two buttons have completely different answers.

### Volume buttons — ✅ already correct, no configuration needed

Android routes the volume keys to the **media stream** whenever media is playing. Because our design keeps the video element playing continuously (§3.1), media is *always* playing — so the volume keys always adjust nursery audio. Exactly the E10 behaviour, for free.

**Do NOT enable Fully's "Disable Volume Buttons."** It's there to stop kiosk users changing volume; here the volume buttons are a feature.

**One consequence to accept:** Fully does not report volume back to HA, so after a hardware volume change, `input_number.nursery_monitor_volume` no longer matches reality. Treat the helper as the **default wake volume** and the hardware buttons as in-session adjustment. Don't build a sync mechanism — there's nothing to sync against.

### Power button — ❌ cannot be remapped, ✅ but HA can follow it

**Android reserves the power key at the system level.** It's handled before any app sees it, so no normal app — Fully included — can intercept `KEYCODE_POWER` and repurpose it. Remapping needs root, and this tablet isn't a rooting candidate.

Fully offers **"Disable Hardware Power Button,"** but that's suppression, not remapping — and the vendor warns it can render a device inoperable. **Not recommended**, especially on a floating device you'll occasionally need to reboot.

**What works instead: let HA adopt the press.** Fully reports screen state to HA, so:

| Action | What Android does | What HA does |
|---|---|---|
| **Press power** | Screen truly off, media suspends | Detects screen-off → runs `script.nursery_monitor_sleep` → state flag goes dormant |
| **Press power again** | Screen on, Fully reloads the start URL | Detects screen-on → runs `script.nursery_monitor_wake` |
| **Cry while powered off** | — | HA turns the screen on remotely (`switch.turn_on`), then wakes normally |

From your hand, the power button now means "put the monitor to sleep / wake it up." The state machine stays coherent, and **a cry still wakes it** — which is the part that actually matters.

### The result: two tiers of standby

| | **☾ Sleep button** (light) | **Power button** (deep) |
|---|---|---|
| Screen | brightness 0, black overlay | genuinely off |
| Audio | playing silently | fully stopped |
| Wake latency on a cry | **sub-second** | **3–8 s** (screen-on + reload + WebRTC renegotiation) |
| Autoplay-gesture risk | none — element never pauses | recovered by Fully's page reload on wake |

Both are legitimate. The ☾ button is the responsive one and should be the habit; the power button is the "I'm putting this in a drawer" one. **Nothing breaks if you use either** — which is the point.

**⚠️ Correction to an earlier claim in this document.** I said Device Owner provisioning "removes the power menu entirely." Fully's own documentation is blunter: *"a very long press on the power button will still cause the most devices to switch off."* Provisioning **reduces** accidental shutdown — it doesn't eliminate it. The real backstop is `automation.nursery_monitor_offline_alert` (§9.2), which catches an off tablet within 5 minutes regardless of how it got there. Treat that automation as load-bearing, not a nicety.

---

## 4. Kiosk software — decided: Fully Kiosk PLUS

**Approved.** €7.90 one-time, per device, perpetual. The E10 model needs remote control of *brightness* and *volume* as independent, instantly-settable numbers, plus unmuted autoplay and a media-file player for the alert tone. Fully has all four as first-class HA entities via the core `fully_kiosk` integration. Nothing else does.

Retained for the record — the two rejected options:

| Option | Why not |
|---|---|
| **HA Companion + screen pinning** (free) | No remote screen/volume control and no unmuted autoplay. §3's state machine is impossible. |
| **WallPanel** (free, open source) | Viable but weaker exactly where it matters: no first-party HA integration (hand-rolled MQTT), and inconsistent autoplay/audio behaviour across Android versions. |

**Known trade-offs accepted:** closed-source single-developer app (bus-factor risk), and occasional WebView quirks after Android updates.

---

## 5. The audio path — ✅ RESOLVED, `nursery_kiosk` stream APPLIED

**⚠️ This section previously said "no NUC edit required." That was wrong, and the correction is worth understanding.**

The camera emits **AAC**; WebRTC carries only **OPUS, PCMU, or PCMA**. Early testing showed audio *playing*, so N2 was closed as "go2rtc transcodes automatically, nothing to do." It does transcode automatically — **but it spawns a separate ffmpeg transcode for every connecting viewer.** Measured that month during a live diagnosis: three concurrent transcodes (Firefox, iOS app, external Safari) and a **2.24 s** WebRTC handshake. The result was choppy video and intermittent audio on every nursery card.

**"It plays" and "it plays reliably" are different tests. Only the second one matters for a baby monitor.**

**Applied that month** — the §5.2 contingency became the fix:

```yaml
# go2rtc: streams:  — LIVE
    nursery_kiosk:
      - ffmpeg:nursery_main#video=copy#audio=opus
```

One persistent AAC→OPUS transcode shared by every viewer instead of N on-demand ones. `video=copy` = no re-encode, negligible CPU. Sourced from `nursery_main` because `nursery_sub` is anamorphic (§6.1).

**All three nursery cards repointed to it:** v3 Nursery view, v3 home pop-up, and the kiosk dashboard.

Applied under the `NUC_ACCESS_SETUP.md` §4a protocol — lock → anchor verified unique on disk → timestamped backup → single targeted insert → `diff -u` (pure addition) → YAML validate → `docker restart frigate` (announced and approved) → healthy at t+36 s → all 4 cameras confirmed at 5 fps → lock released. The config block carries an in-file **DO-NOT-ADD-A-SECOND-BARE-RTSP-LINE** warning, since that is precisely what would expose a talkback backchannel (§5a).

**What was ruled out by measurement — don't re-chase these:** camera link (30/30 pings, 1.46 ms avg, 0.27 ms jitter), NUC load (1.46 across 16 cores), camera health (zero nursery errors in 45 min of logs).

### 5.1 Which stream the kiosk uses

**`nursery_sub`** — 704×480 @ 768 kb/s.

This runs **24/7, dormant included, often on battery** (§3.7). The sub stream costs the Helio G85 and the battery far less than 4.8 Mb/s of 1080p that is black on screen most of the time, and it's comparable to what the E10 itself displays. Swap to `nursery_main` only if the sharper picture proves worth the battery cost, measured at N7.

### 5.2 Contingency — if audio ever breaks

Retained in case a future go2rtc or Frigate upgrade drops the automatic transcode. **Do not apply now.**

```yaml
# go2rtc: streams:  — contingency only, NOT applied
    nursery_kiosk:
      - ffmpeg:nursery_sub#video=copy#audio=opus
```

Uses the precedent already in your config (the doorbell line ends in `#audio=opus`), sources from the existing `nursery_sub` so the camera still sees one connection, and `video=copy` means no re-encode. If it's ever needed, it's a **NUC edit following `NUC_ACCESS_SETUP.md` §4a exactly:** take `/home/claude/.edit-lock` → re-read `config.yaml` from disk → timestamped backup → targeted Python replacement asserting `count == 1` → `diff -u` → YAML validate → `docker restart frigate` (**never `compose down`**) → confirm `(healthy)` → release the lock. Roll back on any failure.

### 5a. ⚠️ One-way only — NO TALKBACK

**Hard requirement: audio flows nursery → tablet, never the reverse.**

**⚠️ Correction to Rev 2/3.** Earlier revisions claimed the stream shape itself guaranteed this, because the proposed `nursery_kiosk` entry would have been `ffmpeg:`-wrapped and an ffmpeg-wrapped source cannot carry a backchannel. **That stream is no longer being created** (§5), so that layer is gone — and the streams we *are* using, `nursery_main` and `nursery_sub`, are **bare RTSP sources**, which is exactly the shape that *can* expose a backchannel on a camera that supports one. The Dahua at `<CAMERA_IP>` plausibly does.

So the honest position: **two enforcement layers, not three.**

1. **The card requests no microphone.** `advanced-camera-card` only offers talkback when a `microphone` block is configured. The nursery card gets none — no button rendered, nothing to tap.
2. **The tablet has no microphone permission** (§8.6) — and no camera permission either, since walk-up detection is out. Fails closed at the OS regardless of any HA or go2rtc misconfiguration.

Layer 2 is the strong one: without OS mic access, the tablet has nothing to transmit. That is sufficient for the stated requirement.

**Optional hardening (§11.4)** — go2rtc supports disabling the backchannel at the source, e.g. appending `#backchannel=0` to the RTSP lines. That would restore a config-level guarantee. It is a **NUC edit**, the exact syntax should be verified against the installed go2rtc version before applying, and it touches streams that Frigate's detect and audio roles depend on. **Not proposed for v1** — the two layers above already meet the requirement, and this project is otherwise not touching `config.yaml` at all.

The `webrtc: candidates:` block annotated *"WebRTC is required for two-way talk"* refers to the doorbell and to the transport generally. It must stay for the nursery live view to work at all.

---

## 8. Android device prep — Device Owner, no Google account

**Decided: provision as Device Owner, and put no Google account on the device.** These two reinforce each other — **Device Owner provisioning requires a device with zero accounts on it**, so "no Google account" isn't just a preference, it's a prerequisite. Both confirmed workable against Fully's own documentation:

- **The APK downloads directly** from fully-kiosk.com. No Play Store needed. It's also the *better* install: Fully installed from Google Play cannot install or uninstall APK files.
- **The PLUS licence can be purchased without a Google account** — Fully documents an instant-licence path explicitly for this case. Buy from their site, not via Play billing.
- **Provisioning strips the device for you.** Fully's docs: *"By default most pre-installed apps are disabled by device provisioning."* The old "remove every preinstalled app" step now happens automatically.
- **Provisioning unlocks Lock Task Mode** (Device-Owner-only) — a harder kiosk than the standard mode: home and recents genuinely disabled, not merely intercepted.

### Order of operations — the order matters

1. **First boot, then update to Android 15.** Take every OS patch now, while the device is still disposable. An account at this stage is fine — it gets wiped in step 2.
2. **Factory reset.**
3. **Boot into the setup wizard. Connect Wi-Fi. Skip every account step.** If any account lands on the device, Device Owner provisioning will refuse and you are doing step 2 again.
4. **Provision Fully as Device Owner.** Two documented methods: the **QR method** (tap the wizard's welcome screen six times to open the QR reader — no computer needed) or **ADB** (`adb shell dpm set-device-owner ...`). **Read the exact QR payload / receiver class off Fully's provisioning page at build time — do not guess it.** A wrong receiver name fails at exactly the moment you are standing over a factory-reset tablet.
5. **Buy and apply the PLUS licence**, then enable **Remote Admin** with a password.

   ⚠️ **Enabling Remote Admin does NOT start the service — Fully must be restarted.** Observed that month: the toggle was set and the password entered, yet nothing on the LAN answered on port 2323, and Fully Cloud's own remote view reported `Remote Admin service running: false` while successfully relaying to the device (so: network fine, app running, service simply not started). **Fix: Fully menu → Restart App.** Port 2323 came up immediately after.

   **Two diagnostics worth reusing:** an unlicensed Fully shows a **watermark** on screen — that's the fast way to tell a licence problem from a service-start problem, since both present as Remote Admin being unreachable. And ping jitter is a reliable sleep indicator: the tablet read 5–46 ms with 16 ms mdev while dozing versus **2.9–7.3 ms with 1.5 ms mdev** awake.
6. **Turn OS auto-update off** now that you are on 15. A monitor that reboots itself for an update is a monitor that was off when you needed it.
7. **Android settings:** Developer options → **Stay awake while charging**. Auto-brightness **off** (HA owns brightness). Screen timeout **never**. Do Not Disturb **on, always**. Lock screen **none** — a swipe-to-unlock is a 3 a.m. tax. Auto-rotate **off**, landscape. All notification sounds **off**. **Exempt Fully from battery optimization / adaptive battery.**
8. **Network:** 5 GHz, static DHCP reservation on the Deco (by MAC, so it follows the tablet room to room).

   **✅ ASSIGNED that month — `<TABLET_IP>`, MAC `AA:BB:CC:DD:EE:FF`, reserved on the Deco.**

   ⚠️ **Turn OFF Android's per-network MAC randomisation before reserving** (Wi-Fi → SSID → Privacy → **Use device MAC**). The tablet first joined as `AA:B7:…`, then as `96:25:…` — both randomised, both would have broken the reservation on the next factory reset or network re-join. **Quick check: if the second hex digit of the first octet is 2, 6, A, or E, the address is software-generated, not hardware.** `98:2B:A6` (digit `8`) is a real vendor OUI, so this one is stable.
9. **Add the Fully Kiosk integration in HA** — device IP + Remote Admin password.

### Fully settings — the ones that matter

| Setting | Value | Why |
|---|---|---|
| Start URL | `http://homeassistant.local:8123/nursery-monitor/monitor` | — |
| **Android Display size** (NOT a Fully setting) | **one or two notches smaller** | **⚠️ THE LAYOUT SETTING — and it lives in Android, not Fully.** At default density the tablet's CSS viewport is only ~893×533, which HA fits into **2** section columns (min column width is a hard-coded 320 px), forcing camera and status tiles to equal halves. Shrinking Android's display size lowers the density → more CSS pixels → ~1190×710 → **3** columns, so the camera spans 2 and the tiles take 1. Render-verified at 1190×710. **Settings → Display → Display size and text → Display size.** Do NOT solve this by redesigning the dashboard — `max_columns: 3` + `column_span: 2` is already correct. |
| **Autoplay Videos** + **Autoplay Audio** (Web Content Settings) | **BOTH ON** | *The settings the whole audio design rest on.* ⚠️ **CORRECTION: there is no "Media playback requires user gesture" option in Fully** — earlier revisions of this doc named the underlying Android WebView API (`setMediaPlaybackRequiresUserGesture`) rather than the UI label. These two toggles are what set it. Don't go looking for the API name. **Caveat from Fully's own docs:** they say autoplay "works only with websites having a static `<video>`/`<audio>` tag" — `advanced-camera-card` creates its video element dynamically for WebRTC, so this is verified by ear, not by assumption. |
| Keep screen on · Launch on boot | ON | — |
| **Microphone permission** | **DENIED** | §5a layer 2 — the strong one |
| **Camera permission** | **DENIED** | No walk-up detection (§3.2) |
| Kiosk Mode + **Lock Task Mode** | ON | Lock Task Mode is Device-Owner-only and strictly better |
| Kiosk exit PIN | set | Stops a stray swipe leaving kiosk |
| Reload start URL on screen-on | ON | Recovers unmuted audio after a power-button standby (§3.8) |
| Screensaver / screen-off timer | disabled / 0 | HA owns the dormant state via brightness |
| Auto-reload on connection loss | ON | — |
| Reload start URL after idle | ~120 s | — |

### ⚠️ Four settings to deliberately leave alone

1. **~~"Shutdown on Power Disconnect" → 0~~ — ⚠️ CORRECTION: this setting is under *Root Settings (PLUS, rooted devices only)* and does not exist on this tablet.** It was flagged as the most dangerous default in an earlier revision; on a non-rooted device it cannot fire, so it is a non-issue. **The setting that DOES apply is "Sleep on Power Disconnect"** (Power Settings) — *hibernate device when power cord is unplugged*. Same failure in a milder form, and on a tablet that is unplugged by design it must be **OFF**. I turned it off that month. Don't go hunting for the root-only one.
2. **"Disable Hardware Power Button" → OFF.** Vendor warns it can render a device inoperable, and you need reboot access on a floating device (§3.8).
3. **"Disable Volume Buttons" → OFF.** The volume keys are a feature here (§3.8).
4. **"Disable ADB" → OFF.** It is the recovery path if kiosk lockdown goes wrong. Disabling it on a provisioned tablet can leave you with no way in short of another reset.

**Updates after lockdown:** no Play Store means Fully updates are manual APK sideloads — or Fully's own "APK Files to Install" + update-interval mechanism, which self-updates from a URL. Recommend leaving both off: this is a frozen appliance, and an unattended update to the monitor app is exactly the kind of surprise §9 exists to prevent.

---

### 8.9 Battery optimisation — where the setting actually is

**It is NOT in Settings → Battery.** That menu covers the *device*, not per-app policy, which is why it looks missing.

**Path: Settings → Apps → See all apps → Fully Kiosk Browser → App battery usage → Unrestricted.** Some builds label the entry just **Battery**. Shortcut: long-press the Fully icon → **ⓘ App info** → Battery. On older Android the equivalent is Settings → Battery → Battery optimization → dropdown "All apps" → Fully Kiosk Browser → **Don't optimize**.

**Why it matters:** without it, Doze can suspend Fully's network sockets while the screen is off. The whole point of this device is that it reacts to a cry event *while dormant*, so a suspended socket is a silent total failure of the product.

**⚠️ Do not go looking for a Fully-side equivalent on a guess.** Three Fully settings have been named on this project that do not exist — "Website Zoom" (the real answer was Android Display size), "Media playback requires user gesture" (the real ones are Autoplay Videos / Autoplay Audio), and "Shutdown on Power Disconnect" (root-only; the applicable one is *Sleep* on Power Disconnect). **Verify a Fully menu label on the device before writing it into this document.**

---

## 9. Reliability

### 9.1 Never show an ambiguous black screen
**Any failure state must be visually distinct from DORMANT.** This is the sharpest trap in the build, because DORMANT is *itself* a black screen — a dead camera at 2 a.m. must not look identical to a quiet nursery. The STREAM DOWN overlay has to be able to appear over the dormant overlay, or wake the panel outright. Design it explicitly; it's an N5 acceptance criterion.

### 9.2 Watch the watcher
`automation.nursery_monitor_offline_alert` is the whole reason this isn't just a dashboard. Tablet drops Wi-Fi, Fully crashes, battery dies → push within 5 minutes. Paired with the 20 % low-battery warning (§7.3) so a floating tablet gives you warning before it goes quiet. Test by pulling the plug once, and again after any Android update.

### 9.3 Battery
Floating use means natural charge cycling — no smart plug needed. Expect **~5–8 h unplugged** with a live decode; **measure this during bake-in**, because it determines whether the optional battery-saver mode (§3.7) is worth building.

### 9.4 Camera stability
The nursery camera's `hwaccel_args: []` (software decode) is **load-bearing** — your config comments record hardware decode crash-looping every ~3 min, taking `camera.nursery` down ~20 s each time. Don't let a future Frigate cleanup delete it. This project makes that line safety-critical rather than merely annoying.

---

## 10. Build phases

| Phase | Work | Est. |
|---|---|---|
| **N1** | ✅ **COMPLETE that month.** OS update → factory reset → Device Owner provisioning (no Google account) → PLUS licence → Fully config → HA integration (33 entities). Final three settings closed out that month: **Start URL** (verified live — `sensor...current_page` reads `http://homeassistant.local:8123/nursery-monitor/monitor`, `foreground_app` = `com.fullykiosk.emm`), **Android Display size**, **Battery → Unrestricted**. ⚠️ **Still OFF and deliberate-or-not-yet-decided:** `binary_sensor...kiosk_mode`, `switch...kiosk_lock`, `binary_sensor...device_admin`. | done |
| **N2** | ✅ **COMPLETE.** Audio confirmed on `nursery_sub`. No NUC edit needed (§5). | done |
| **N3** | ✅ **COMPLETE.** `input_datetime.nursery_last_cry` + `automation.nursery_stamp_last_cry` live, area/label/category applied, `HA_Reference.md` reconciled 2,059 → 2,084, Repairs 0. Built as input_datetime + stamping automation (the `nursery_last_woke` house pattern), **not** the trigger-template sensor originally proposed — trigger templates need YAML. | done |
| **N4** | ✅ **Helpers COMPLETE** — area `Floating Devices`, label `kiosk`, state flag, 2 timers, 3 input_numbers; `HA_Reference.md` reconciled 2,084 → 2,090, Repairs 0. **Chime: 3 candidates generated** (`nursery_monitor/chime{A,B,C}*.mp3`) awaiting my pick. **Wake/sleep scripts deferred to N1** — they all end in `fully_kiosk` calls. | mostly done |
| **N5** | ✅ **COMPLETE.** Dashboard `nursery-monitor` + theme `nursery_monitor.yaml` shipped and render-verified at **both** 893×533 and 1340×800. Dormant overlay confirmed full-viewport black + tappable; both alert banners confirmed via a temp view (created, shot, deleted). Three frontend lessons banked in §6.1. `HA_Reference.md` reconciled 2,090 → 2,093, Repairs 0. | done |
| **N6** | ✅ **COMPLETE that month.** 2 scripts + 6 automations live, area `Floating Devices`, labels `kiosk`+`baby`, category *Nursery Monitor*, icons set. `HA_Reference.md` reconciled 2,163 → 2,171, Repairs clean. **Verified by template evaluation only — nothing has been RUN.** See §7.36 for the six design decisions and the outstanding live tests. | done |
| **N7** | **1-week bake-in**: tune the 10 s qualifier and `min_volume`, measure battery life, decide on battery-saver mode. Then regenerate `HA_Reference.md` per the CLAUDE.md rule. | — |

N4 and N5 don't need the tablet and can run before N1. **Do not start N1 casually** — step 3 (skip every account) is unforgiving, and getting it wrong means another factory reset.

---

## 11. Open items

### ⚠️ 11.0 REVERT BEFORE CALLING THIS DONE — temporary alert audience

**Set that month at my request, for the duration of the build-out only.** Both baby-monitor alert automations were narrowed to my phone so setup testing doesn't repeatedly blast my wife with critical alerts:

| Automation | Was | Now (temporary) |
|---|---|---|
| `automation.nursery_baby_crying_critical` | `notify.parents` | `notify.parents` |
| `automation.nursery_camera_offline_heartbeat` (both branches) | `notify.parents` | `notify.parents` |

**This is a safety regression while it stands** — the cry alert and the monitor-is-dead alert currently reach exactly one phone. If that phone is silenced, face-down, or out of the house, nobody is told. Acceptable during active setup; **not** acceptable as the resting state.

**⏸️ DECIDED: HOLD the phone-only audience through the N7 one-week bake-in, then revert.** Rationale: N7 exists to tune the cry qualifier and `min_volume`, which means deliberate test fires at unpredictable hours; routing those to the full group would wake my wife repeatedly for non-events. **This makes the revert an explicit N7 EXIT CRITERION, not an N6 task — N7 is not complete until the audience is restored.** The safety regression below stands until then, knowingly.

**Revert when the tablet is stable and complete.** Both automations carry a `⚠️ TEMPORARY AUDIENCE` banner at the top of their description naming the original target, so the correct value is recoverable from the instance itself even if this document is lost. The N6 automations (`_offline_alert`, `_low_battery`) are specced against `notify.parents` and should be reviewed at the same time — a *tablet* battery warning is genuinely for me only, but a *monitor is dead* alert is not.

---

All ten original questions are answered and folded in above; Device Owner provisioning is now **decided and specified in §8**. Four things remain, none blocking:

1. ✅ **Chime chosen** (rising bell, §3.5). Remaining: **I uploads `nursery_alert_chime.mp3` to `www/nursery_monitor/`** — 2-minute File-editor step the connector can't do (binary).
2. **Battery-saver mode** — decide after N7 measures real battery life (§3.7).
3. **Control drawer (v2)** — lights, white noise, minisplit, and the ground-truth buttons, once v1 is stable (§6).
4. **Backchannel hardening** — optional `#backchannel=0` on the nursery RTSP sources (§5a). Not needed for the no-talkback requirement; would restore a config-level guarantee at the cost of a NUC edit this project otherwise avoids entirely.
5. **Exact provisioning payload** — read the QR payload / device-admin receiver class off Fully's provisioning page immediately before N1 (§8 step 4). The only genuinely unknown value in the whole build, and the one that fails at the worst moment if guessed.

---

## 12. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| **STREAM DOWN indistinguishable from DORMANT** | **Medium — the design trap** | Explicit overlay precedence (§9.1), N5 acceptance criterion. |
| Brightness 0 still visibly glows in a dark room | Medium — verify early | Full-screen black overlay (§3.3). If it still glows, revisit true screen-off with the audio-resume risk understood. |
| Battery life too short for floating use | **Medium — unmeasured** | 20 % low-battery alert; optional battery-saver mode after bake-in (§3.7). |
| Dormant overlay swallows taps → no way to wake it | Medium | Overlay is a tap target (§3.2). N5 acceptance criterion. |
| **Accidental shutdown via long-press power** | Low–medium | Silent, and the worst outcome available — a monitor that is simply off. **Device Owner reduces but does NOT eliminate this**; Fully's docs say a very long press still powers off most devices (§3.8). `automation.nursery_monitor_offline_alert` (§9.2) is the real backstop and is load-bearing. |
| **"Shutdown on Power Disconnect" left at a non-zero default** | Low, high impact | Would power the tablet off every time it's unplugged — and it's unplugged constantly by design. Explicit N1 checklist item (§8). |
| Provisioning fails because an account got added during setup | Medium at N1 | Skip every account step in the wizard; if it fails, factory reset and retry. Cheap to redo, annoying to diagnose. |
| False wakes at 3 a.m. | Medium | Three tunable layers (§3.4); `min_volume` first, then the qualifier. Bake-in week exists for this. |
| Unmuted autoplay blocked despite the Fully setting | Medium | Fails at page load, where it's visible and testable — not mid-night. Fallback: scheduled reload + visible mute-state indicator. |
| Media element pauses and silently refuses to resume unmuted | Low **by design** | The element never pauses — volume 0, not stopped (§3.3). |
| **Missed** cry — qualifier too high | Low–medium | `automation.nursery_baby_crying_critical` phone push stays as an independent second channel. |
| Tablet carried into the nursery → audio feedback loop | Low–medium | Presence suppression + forced volume 0 when nursery presence is on (§3.7). |
| Talkback silently enabled later | Low | **Two** layers, not three (§5a correction): no `microphone` block on the card, and no OS mic permission on the tablet. The second is sufficient on its own. Optional `#backchannel=0` hardening available (§11.4). |
| Camera ffmpeg crash-loop returns | Low | `hwaccel_args: []` stays; overlay + heartbeat automation cover it. |
| NUC config edit collides with another writer | Low | Advisory lock + re-read from disk, per `CLAUDE.md`. |

---

## 13. Reference obligations

Nothing here has been applied. When the build runs, **each phase that creates entities updates `HA_Reference.md` in the same session** — re-read immediately before writing, apply targeted edits, reconcile counts against `ha_get_overview`, update the *Snapshot generated* line, check Repairs, verify the file tail. Never write back a full copy held in context.

New objects needing reference entries: `sensor.nursery_last_cry`, optional cry counter, `input_boolean.nursery_monitor_active`, 2 timers, 3–4 input_numbers, 2 scripts, 5 automations, the Fully Kiosk config entry and its ~10 entities, the `nursery-monitor` dashboard, the `nursery_monitor` theme, **new area `Floating Devices`**, **new label `kiosk`**.
