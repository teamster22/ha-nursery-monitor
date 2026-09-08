# The tablet parent unit

An Android tablet running Fully Kiosk Browser, showing one Home
Assistant dashboard view with the nursery camera on it. The goal was Eufy E10
parity: press a button, see the room, instantly.

It is not wall mounted, and that was deliberate. A parent unit belongs wherever the
parent is, so this one floats: kitchen counter, arm of the couch, handed to a
babysitter on the way out. Everything below follows from that, especially the
battery handling in §3.7 and the low-battery alert in §7.3, which only matter
because the thing spends its life unplugged.

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

## The original build proposal

The long-form working notes behind these decisions, including the latency budget,
the Fully Kiosk setting-by-setting walkthrough, and the risk table, are in
[build-journal/tablet-build-notes.md](build-journal/tablet-build-notes.md). You do
not need them to build this. They are there if you want to know why a choice went
the way it did.

