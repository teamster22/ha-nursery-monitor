# Dashboard layout research

What commercial baby monitors put on screen, and what I copied.

> Read [../DISCLAIMER.md](../DISCLAIMER.md) first. Short version: not a medical
> device, and an LLM wrote essentially all of the code here. I'm not a software
> engineer, so read the config yourself before you run it.


**Purpose:** inspiration and a decision framework for laying out the `nursery-monitor` kiosk. Written after a long build session that produced a working-but-unsatisfying layout.
**Companion:** [tablet-build.md](tablet-build.md) (the build).

---

## 1. The finding that matters most

There is a mature design literature for exactly this class of screen — it just isn't filed under "smart home." It's called the **operational / wall-mounted monitoring dashboard**, and its two governing ideas are:

> **Dark cockpit.** Dark surfaces are a *functional* requirement, not an aesthetic one, for any screen watched in low ambient light. Alerts must pop against the background; color-coded severity has to be instantly scannable.

> **Exception-based display.** The goal is *ambient awareness*: a steady signal that fades into the background when everything is normal, and becomes impossible to ignore the moment something changes.

**Measured against that, the current design is wrong in a specific way.** It shows five or six status chips permanently — state, last cry, door, climate, battery — none of which need attention when things are normal. That is *information density*, which is a reporting-dashboard virtue. A monitor wants the opposite: **near-silence when all is well.**

**The Eufy E10 gets this right by accident of being cheap.** Its parent unit shows video and essentially nothing else. There is no "door closed 3:32 PM" chip because that is not what you are asking the device. You are asking exactly one question — *is she OK?* — and the video answers it.

---

## 2. What each precedent actually teaches

| Precedent | The transferable idea |
|---|---|
| **Eufy E10 / OEM monitors** | One question, one answer. Video *is* the status display. Everything else is an interruption. |
| **Nanit / Miku** (premium monitors) | Data exists but lives **one level down**. The live view is clean; breathing/sleep analytics are a separate screen you go to deliberately. |
| **Operational NOC dashboards** | Exception-based: normal state = quiet. Severity is carried by **color + position**, not by more text. |
| **Aviation "dark cockpit"** | If a light is on, something needs you. Nothing is lit during normal operation. **The absence of indication IS the indication.** |
| **HA wall-panel community practice** | Build a *separate, lighter* dashboard per device; don't reuse a general dashboard. Cheap tablets choke on cards. (We already do this.) |

---

## 3. Three layouts worth considering

### Option A — **Dark Cockpit** (my recommendation)

```
┌──────────────────────────────────────────────┐
│                                              │
│                                              │
│              VIDEO — near full screen        │
│                                              │
│                                              │
│                                              │
│  ASLEEP · 2h 14m                             │  ← single line, bottom-left, dim
└──────────────────────────────────────────────┘
        (tap anywhere → controls slide in for 10s)
```

**Always visible:** video, plus **one** line of text — the state and how long it's held. That is the whole answer to "is she OK?"

**Appears only on exception:**
- **CRYING** — large, red, center
- **STREAM DOWN** — large, red, center
- **DOOR OPEN** — small amber marker (it's abnormal while she's asleep)
- **Tablet on battery < 20 %** — small amber marker
- **CO₂ > 1200 ppm** — small amber marker

**On demand:** everything else. Tap to reveal controls; they auto-hide. Climate, last-cry time, battery % are all *diagnostic* data — useful when you go looking, noise when you aren't.

**Why this is the strongest option:** it maximises video, it matches what the device is actually for, and it removes the failure mode where six always-on chips train you to stop reading any of them.

---

### Option B — **Two-Zone** (closest to current, tightened)

```
┌───────────────────────────────────┬──────────┐
│                                   │ ASLEEP   │
│                                   │ 2h 14m   │
│           VIDEO                   │          │
│                                   │ 69° 60%  │
│                                   │ 1281 ppm │
│                                   │          │
├───────────────────────────────────┴──────────┤
│  ◀ ) )    MUTE    ☀ ▲ ▼            ☾ SLEEP   │
└──────────────────────────────────────────────┘
```

Persistent narrow rail, but **cut to 3 items max** and set in a *dimmer* color than the video so it recedes. Controls as a permanent bottom bar.

**Trade-off:** you keep at-a-glance climate, but you spend ~20 % of the screen on data you rarely act on, and the rail competes with the video for attention every time you glance up.

---

### Option C — **Video Only + Gesture** (the purist option)

Video edge to edge. **Nothing else, ever**, except the two red exceptions. All state and controls live behind a tap.

**Trade-off:** the most faithful to the E10 and the most beautiful — but you lose the one genuinely valuable thing the E10 *doesn't* have: knowing at a glance how long she's been down without waking the panel.

---

## 4. Design rules to apply regardless of option

1. **One thing must be readable from 3 metres.** Currently nothing is. The state word (`ASLEEP`) should be the largest text on screen — it is what you read from the doorway. Everything else can require walking closer.
2. **Reserve color for exceptions.** Red = crying or blind. Amber = worth knowing. Everything normal is gray/white. Right now purple/green/amber state icons spend color on the normal case, which devalues it.
3. **Timestamps are worse than durations.** "Down 7:30" makes you do arithmetic at 3am. "Asleep 2h 14m" doesn't. Prefer elapsed time everywhere.
4. **Controls should be few and large.** Six controls is at least two too many for a device operated half-asleep. Volume ± and Sleep are essential; brightness is arguably automatic (it's already state-driven in §3 of the plan) and Mute duplicates Volume-to-zero.
5. **Never show a number without a threshold.** "1281 ppm" means nothing at a glance. Either color it against a threshold or don't show it.

---

## 5. Concrete recommendation

**Go with Option A**, and specifically:

- **Video ~90 % of the screen.**
- **One persistent line:** state + elapsed (`ASLEEP · 2h 14m`), large, bottom-left, dim gray.
- **Exception markers** appear inline on that same line — door, CO₂, battery — as small amber icons, only when abnormal. No text unless tapped.
- **CRYING / STREAM DOWN** stay as the big red center banners (already built).
- **Controls hidden**, revealed by tapping the video, auto-hiding after ~10 s.

**Why this also solves the technical problem we hit tonight:** far fewer permanently-rendered cards means far less to go wrong, and the exception markers can be plain conditional cards rather than fixed-position overlays. The layout stops fighting the grid because there is almost nothing in it.

**Cost to accept:** you give up always-visible climate. That data is still one tap away, still on the v3 Nursery view, and still driving the automations regardless.

---

## 6. Open question

The single biggest decision is **whether climate (temp/humidity/CO₂) needs to be visible without interaction.**

- If **yes** → Option B, and we tighten it.
- If **no** → Option A, and the design gets dramatically simpler, more reliable, and more video.

Everything else follows from that one answer.
