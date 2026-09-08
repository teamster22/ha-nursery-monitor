# Sensor selection — the original brief

> **Build journal. Superseded, and it specs hardware that was never built.**
>
> The load-cell crib sensor below was designed, priced, and never assembled. The
> software approach in [../nap-detection.md](../nap-detection.md) shipped and made
> it unnecessary. **Do not build from the BOM or the mechanical section** — nobody
> has ever assembled this, and a build guide nobody has followed will burn you.
>
> Kept because the reasoning about *why* certain signals are useless is still
> correct, and because a design doc that only shows the answer teaches nothing.

> Read [../../DISCLAIMER.md](../../DISCLAIMER.md) first. Short version: not a medical
> device, and an LLM wrote essentially all of the code here. I'm not a software
> engineer, so read the config yourself before you run it.


**Purpose:** Everything needed to continue this project in a fresh chat. Paste or attach this file at the start of the new Cowork task.

**Status:** Design agreed. Nothing built yet. Ready to write ESPHome YAML + HA state machine.

**Home Assistant project context:** This is part of the "Home Assistant Administration" project (HA‑MCP connector, mounted folder with `HA_Reference.md` / `HA_Project.md`, dashboard `dashboard-claudetbv3` = "Dashboard v3").

---

## 1. The Goal

Produce a reliable HA entity that answers: **"Is my daughter napping in the nursery?"**

- **Deliverable:** an entity (`binary_sensor.nursery_nap`) with a state of asleep / not-asleep, **plus a `confidence` attribute (0–100)**.
- **Consumers:** dashboard cards, automations (dim hall lights, mute notifications, suppress doorbell, etc.). Each automation picks its own confidence threshold — e.g. lights at ≥50, notification-muting at ≥90.

### The child
- **Toddler, 25+ lb (~11.3 kg).** This is the primary target.
- Should ideally still work for an **infant (~3.2–3.6 kg)** in the future (nice-to-have, not a blocker).

---

## 2. The Core Problem (do not re-litigate)

All the signals currently used are **negative / permissive evidence**: door closed, lights off, no adult present. Those conditions are *identical* for "she's napping" and "the nursery is empty at 2pm." **You cannot reach a confident YES from an absence of contradictions.** At least one **positive** signal is required.

Second structural issue: **a template sensor is stateless.** It recomputes from current conditions and cannot distinguish "door closed because she was just put down" from "door closed because nobody's been in there since breakfast." Therefore the design uses a **state machine**, not a pure template.

---

## 3. Decisions Made

| Decision | Choice | Why |
|---|---|---|
| Ambiguity handling | **Expose a 0–100 confidence score** | Each automation sets its own threshold |
| Positive sensor | **Load cells under the crib LEGS** | Unambiguous, cheap, local |
| mmWave respiration (Seeed MR60BHA2) | **Rejected** | See below |
| Cells under mattress | **Rejected** | See below |
| Cells under mattress tray | **Rejected** | See below |
| Auto-tare | **Required, not optional** | See drift note below |

### Rejected: mmWave respiration (Seeed MR60BHA2)
Initially looked promising (official ESPHome component, pre-flashed firmware, plug-and-play). **Rejected because:**
- User explicitly does **not need respiration granularity** — "there is a child in the crib" is exactly as useful as "breathing at 45 bpm." Respiration was the *only* advantage of this sensor class.
- Real failure mode: **a toddler migrates around the crib** and drifts out of the radar beam → reads as empty.
- Vendor accuracy claims (~90% breathing / ~85% heartbeat) are for **adult** subjects; infant respiratory rates (30–60 bpm vs adult 12–20) may fall outside its tuned band. Unverified risk.

### Rejected: load cells under the mattress (pucks on the tray)
**Fatal flaw, identified by user:** a soft/springy mattress **sags between the pucks and bottoms out on the tray underneath**, shunting an unknown and *variable* fraction of the load away from the cells. Readings would change depending on where in the crib she lies. Unusable.

### Rejected: load cells under the mattress tray
Workable in principle (rigid tray = rigid load path) but requires the tray to **float** on the cells only — fighting bolts/brackets/ledges. A rigid sub-plate variant also **raises the mattress**, which **lowers effective rail height** — a real safety consideration for a climbing-age toddler. Not worth it.

### ✅ Chosen: load cells under the four crib LEGS
Load path becomes: child → mattress → tray → crib frame → **4 legs → 4 load cells → floor**. That path is **guaranteed** — the crib already rests on exactly those four points and nothing else. Nothing to sag, bridge, or shunt. The mattress is untouched and fully supported as the manufacturer intended.

**Bonus wins:**
- **No mattress-height change** → rail-to-mattress geometry (and climb-out safety) is unaffected.
- No tray surgery, no bolt fighting.
- Installs/removes in ~10 minutes.
- Well-trodden pattern (DIY bed-occupancy sensors have used 4 cells under bed legs for years).

---

## 4. Critical Technical Findings (corrections discovered along the way)

### ⚠️ Drift is worse than expected — auto-tare is REQUIRED
Short-term noise is good (**±10–25 g**), but these cells **drift**: left overnight, the zero can wander by **as much as ±1 kg** ([Circuit Journal](https://circuitjournal.com/50kg-load-cells-with-HX711)).

- For an **11.3 kg toddler** vs a 3 kg threshold: non-issue (8 kg headroom).
- For a **3.2 kg newborn** vs a 2 kg threshold: **a +1 kg drift would report an empty crib as occupied.**
- ⇒ **Auto-tare is mandatory** for the future-infant case. It was initially called optional. That was wrong.

**Auto-tare rule (important):** HA presses `button.crib_tare` **only when the room is *provably* empty** — door open **AND** adult presence detected **AND** weight stable for 60 s.
**NEVER auto-tare on "weight has been stable and low" alone — that is exactly how you tare away a sleeping child.**

### "Still vs. moving" — how it actually works under the legs
With cells under the legs, **total weight is constant regardless of where she lies.** Position gives you nothing. What you measure is **dynamic force**: when she kicks/rolls/sits up/pulls to stand, she accelerates her mass (`F = ma`), producing real fluctuations in measured load.

- **Still, sleeping child → flat trace. Moving child → noisy trace.** Exactly the wanted discrimination.
- Gross toddler movement = force swings of **hundreds of grams to kilograms** vs a ~±10 g noise floor. Very detectable.
- ❌ **Breathing is NOT achievable.** Respiration is a grams-level force change, at/below the noise floor of a 200 kg-full-scale bridge carrying a ~20 kg crib. **Do not expect or promise respiration from this build.** (Acceptable — user doesn't want it.)

### Confound to guard
An **adult leaning on the crib rail** adds weight and looks like the child got heavier. Guard using `binary_sensor.nursery_presence_sensor` — if an adult is in the room, don't trust a *transition*. (Composes cleanly with the auto-tare rule, which also requires adult presence.)

---

## 5. Hardware — Bill of Materials (~$25–30)

| Part | Notes | ~$ |
|---|---|---|
| 4× 50 kg half-bridge load cells | Bathroom-scale type, 3 wires each (white / red / black) | $10 |
| HX711 breakout | 24-bit ADC; runs at 3.3 V | $3 |
| ESP32 (or XIAO ESP32-C3/C6) | 3.3 V — no level shifting needed | $5–10 |
| Wire, small terminal block, USB PSU | — | $5 |

4 × 50 kg = 200 kg capacity. Huge overkill for ~20 kg of crib + child, but fine — the 24-bit HX711 still resolves ~±10 g.

**User has a 3D printer** — printing the pucks is expected.

---

## 6. Mechanical Build

### The #1 failure mode
Each cell is an aluminium block with an **inner pad** and an **outer rim**. It only works if **the inner pad can flex relative to the outer rim.** Sandwich it flat between two surfaces and it reads nothing.

### Puck design (print 4, as under-leg feet)
- **Base cup** supports the **outer rim**; **top cap** bears *only* on the **inner pad**, with **1–2 mm clearance** all around so nothing bottoms out during deflection.
- Reference two-part frame: [Thingiverse thing:2624188](https://www.thingiverse.com/thing:2624188) (outer shell + spacer ring).
- **Wide base** — noticeably wider than the crib leg so the crib cannot tip or walk off. *Over-engineer this one.*
- **Shallow cup/recess on top** to capture the crib leg so it can't slide out.
- **TPU / rubber pad underneath** for grip. On carpet, add a rigid plate under each puck so it doesn't sink and rock.
- **PETG (not soft PLA), thick walls, high infill** — these carry the crib's full weight.
- **All four identical height**; level the crib afterward.

Cell wires run down/along the floor to a junction → HX711 + ESP32 in an enclosure outside the crib. (Cable routing out of child's reach — already accounted for by user.)

---

## 7. Wiring (4× half-bridge cells → one full Wheatstone bridge → HX711)

Do **not** improvise this. Exact topology:

1. **Form a ring:** link the *outer* wires (white ↔ black) of the four cells in a loop.
2. The four **red** (middle) wires are the bridge nodes. Opposite reds form the two **diagonals**.
3. **Verify with a multimeter BEFORE powering anything:** each red-to-red diagonal should read **~2 kΩ**. If not, the loop is wrong.
4. One diagonal (2 reds) → HX711 **E+ / E−**. The other diagonal → **A+ / A−**.
5. **Polarity doesn't matter** on either pair — swapping just inverts the calibration constant.
6. HX711 **VCC → 3.3 V**, **GND → GND**, **DT** + **SCK** → any two GPIOs.

**Per-cell sanity check:** resistance across the two outer wires ≈ **2 kΩ**; outer-to-red ≈ **1 kΩ**. Confirms which wire is the middle tap.

---

## 8. ESPHome — target shape (needs to be written in full)

```yaml
sensor:
  - platform: hx711
    id: crib_raw
    internal: true
    dout_pin: GPIO16
    clk_pin: GPIO17
    gain: 128
    update_interval: 0.5s
    filters:
      - calibrate_linear:
          - 0 -> 0
          - 500000 -> 11.30      # raw reading with a known ~11.3 kg on it
      - median: {window_size: 7, send_every: 2}

  - platform: template            # net of crib + mattress + bedding
    name: "Crib Weight"
    id: crib_net
    unit_of_measurement: kg
    lambda: 'return id(crib_raw).state - id(tare_kg);'
    update_interval: 1s

  - platform: template            # movement proxy (dynamic force)
    name: "Crib Restlessness"
    lambda: 'return fabs(id(crib_fast).state - id(crib_slow).state);'
    update_interval: 1s

binary_sensor:
  - platform: template
    name: "Crib Occupied"
    device_class: occupancy
    lambda: |-
      if (id(crib_net).state > 3.0) return true;   // in
      if (id(crib_net).state < 1.5) return false;  // out
      return {};                                   // hysteresis: hold previous
    filters:
      - delayed_on: 20s     # ignore a lean-over during put-down
      - delayed_off: 30s    # ignore a brief lift / reposition

button:
  - platform: template
    name: "Crib Tare"
    on_press:
      - lambda: 'id(tare_kg) = id(crib_raw).state;'
```

**Still to write:** wifi/api/OTA blocks, `globals` (`tare_kg`, restore_value), the fast/slow `platform: copy` sensors feeding restlessness (or a rolling stddev), enclosure/pin finalization.

`return {}` in the middle band is what gives hysteresis (holds previous state instead of chattering).

### Calibration procedure
1. Empty crib (mattress + bedding in place) → press **Tare**.
2. Put a known weight on it (10 kg dumbbell, or step on it and use your own bathroom-scale weight) → read raw → plug into `calibrate_linear`.
3. Thresholds: **>3 kg = in, <1.5 kg = out** (toddler). Comfortably above bedding (<1 kg) and drift.

### Entities this produces
`binary_sensor.crib_occupied` · `sensor.crib_weight` · `sensor.crib_restlessness` · `button.crib_tare` — all local via ESPHome, auto-discovered.

---

## 9. HA Software Layer (sensor-agnostic — can be built BEFORE the hardware arrives)

**Layer 1 — state machine**
- `input_select.nursery_state`: `awake` / `settling` / `asleep`
- `input_datetime.nursery_nap_started` (gives nap duration for free)

**Layer 2 — automations**
- **Nap start:** triggered by a positive event (wall-remote button, `crib_occupied`, Sonos starts), conditioned on guards (door closed, lights off, illuminance low, no adult), with a `for:` debounce — e.g. door closed + no adult **for 2 minutes** before declaring asleep.
- **Nap end:** triggered by any contradiction — door opens, lights on, adult presence sustained >30 s, Sonos stops, crib unoccupied, or manual override.

**Layer 3 — the deliverable**
- `binary_sensor.nursery_nap` (`device_class: occupancy`) with attributes: `started_at`, `duration`, **`confidence` (0–100)**.
- Confidence = weighted sum across: **crib occupancy (highest weight)**, crib stillness, Sonos playing, wall-remote button, door closed, lights off, illuminance, no adult present, time-of-day window.

**Layer 4 — card**
- Mushroom template card: state, elapsed nap duration, confidence, and which signals are currently contributing.

**Debounce/hysteresis is what makes this feel reliable rather than flickery — naive implementations always get this wrong.**

---

## 10. Existing Nursery Entities (verified live)

| Entity | Role |
|---|---|
| `binary_sensor.nursery_door_open` | negative guard (door open ⇒ not napping) |
| `binary_sensor.nursery_presence_sensor` | mmWave, HomeKit — **detects adults only**; adult present ⇒ not napping. Also guards the rail-lean confound + gates auto-tare. |
| `sensor.nursery_presence_sensor_light_sensor_light_level` | true illuminance — better than light entity state (catches daylight / blackout shades) |
| `light.nursery_lights` (group) | negative guard |
| `light.nursery_overhead_lights` | negative guard |
| `light.nursery_table_lamp` | negative guard |
| `media_player.sonos_nursery` | ⭐ **positive** signal (white noise / lullaby persists through the nap) |
| `event.nursery_wall_remote_scene_001..004` | ⭐ Aeotec WallMote Quad — **4 free buttons**; dedicate one to nap start/stop = **ground truth** |
| `automation.zwavejs_aeotec_wallmote_quad_scene_controller` | "Nursery Hub Buttons" — existing handler for the above |
| ~~`input_button.bb_sleep_helper`~~ | **REMOVED later — Baby Buddy deprecated and fully uninstalled.** Do not wire it. (It was the only BB sleep hook; BB never exposed a sleep-state sensor.) |
| `binary_sensor.nursery_window_opening` | context |
| `binary_sensor.magic_areas_presence_tracking_nursery_area_state` | Magic Areas area rollup |
| `climate.nursery_minisplit` | context |
| `sensor.nursery_airthings_*` | temp / humidity / CO2 context |
| `input_boolean.nighttime` | day-vs-night context |
| `automation.nursery_dim_presence_light` | existing nursery automation |

---

## 11. Safety Framing (keep this line)

**This is convenience automation, NOT a medical or breathing monitor.** Load cells and mmWave radars are consumer devices. Nothing in this build should be relied upon for the child's wellbeing or safety monitoring. Do not let a nap sensor become something that gets trusted for that purpose.

---

## 12. Next Steps

1. ☐ Write the **complete ESPHome YAML** (wifi/api/OTA, globals, fast/slow copy sensors, rolling-stddev restlessness, occupancy hysteresis, tare button).
2. ☐ Design/print the **4 under-leg pucks** (wide base, leg cup, 1–2 mm inner-pad clearance, PETG).
3. ☐ Build the **HA software layer** (state machine + confidence sensor + card) — *can be done now, before hardware arrives*, using the existing signals; crib sensor slots in later as the top-weighted input.
4. ☐ Wire a spare **wall-remote button** as manual nap start/stop ground truth.
5. ☐ Build the **auto-tare automation** (door open + adult present + weight stable 60 s).
6. ☐ Calibrate, then tune thresholds/weights against real naps.

---

## Sources
- [50kg Load Cells with HX711 — 4x/2x/1x wiring diagrams (Circuit Journal)](https://circuitjournal.com/50kg-load-cells-with-HX711)
- [SparkFun HX711 Load Cell Amplifier Hookup Guide](https://learn.sparkfun.com/tutorials/load-cell-amplifier-hx711-breakout-hookup-guide/all)
- [Thingiverse load cell mounting frame (thing:2624188)](https://www.thingiverse.com/thing:2624188)
- [ESPHome HX711 component](https://esphome.io/components/sensor/hx711/)
- [ESPHome Seeed MR60BHA2 component (rejected option, for reference)](https://esphome.io/components/seeed_mr60bha2/)
