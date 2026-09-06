# The wall remote (ground truth)

Two holds on a Z-Wave wall remote declare ground truth: **hold top-left** means
"she's down," **hold bottom-left** means "she's up."

## Why this exists

You cannot score an inference machine without something to score it against. In
shadow mode these two holds write **only** `input_select.nursery_ground_truth` and
deliberately do not touch `input_select.nursery_state`, so the inferred state and
the declared state stay independent and you can actually measure how often the
machine is right.

Run it that way for a couple of weeks before you wire the override in. If you skip
this step you will never know whether the thing works, you'll only know that it
hasn't obviously failed.

## What I used

An Aeotec ZW130 WallMote Quad, driven through the community blueprint
`robinsmidsrod/zwavejs-aeon-labs-aeotec-zw130-wallmote-quad-all-scenes-supported`.
All four **taps** were already bound to lights, and both right-hand **holds** were
bound to dimming, which left the two left-hand holds free.

**The light-control automation is not in this repo.** It's a blueprint instance tied
to a specific device ID, it's household light control rather than part of the
monitor, and a device ID from my registry is useless in yours. Wire your own.

## Any button will do

Nothing about the design needs Z-Wave or that specific remote. The nap automation
(`Nursery Nap 5`) triggers on `event.nursery_wall_remote_scene_001` and
`_scene_003` with `event_type: KeyHeldDown`. Point those triggers at whatever
produces events in your house: a Zigbee button, a Lutron Pico, a dashboard button,
an NFC tag by the door.

What matters is that declaring ground truth is **one deliberate gesture** you can do
in the dark on your way out of the room, without unlocking a phone.
