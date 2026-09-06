# Disclaimer

**This is not a medical device. It is not a breathing monitor. Do not rely on it for
a child's wellbeing.**

Read that again, because it's the only part of this repository that really matters.

## What this is

Convenience automation. It watches a door sensor and a presence sensor to guess
whether a child is asleep, and it listens to a camera's audio stream for crying so
it can push a notification to a phone. That's the entire scope.

## What it is not

It does not monitor breathing, heart rate, oxygen saturation, temperature, or
movement. It cannot detect SIDS, apnea, choking, entrapment, overheating, or any
other medical emergency. It has no alarm for the absence of a signal, because it has
no signal that corresponds to a child being alive.

A silent nursery and a healthy sleeping child produce exactly the same output from
this system. So does a silent nursery and an emergency.

## The specific ways it will fail you

Every one of these has either happened or is a known property of the parts involved.

**The cry detection is a machine-learning classifier and it misses things.** It runs
on Frigate's YAMNet audio model with a confidence threshold. It will miss quiet
distress. It will occasionally fire on something that isn't a cry. A whimper below
the volume floor produces nothing at all.

**The nap state can be wrong and still look confident.** It infers from a door
contact and a presence sensor. If the door sensor drops an event, the machine can
sit in the wrong state indefinitely. The confidence decay exists specifically to
catch that, which tells you it's a real failure mode rather than a hypothetical.

**mmWave presence sensors see through walls.** I measured a presence event firing
through a closed door, almost certainly picking up someone in the hall. The design
works around it, but the sensor is not trustworthy on its own.

**Every link in the chain can go down silently.** Wi-Fi, the camera, Frigate, Home
Assistant, the notification service, the phone's own do-not-disturb settings. There
are watchdog automations here for the camera and the tablet, and a watchdog only
tells you about a failure it was written to expect.

**The tablet is a tablet.** It can crash, run out of battery, lose the stream, or
sit there displaying a frozen last frame that looks exactly like a quiet room.

## Use it the way I use it

As a second pair of eyes on top of ordinary parental attention, safe-sleep practice,
and whatever your pediatrician tells you. Not as a substitute for any of them.

If you want a device that actually monitors an infant's vital signs, buy a
regulated medical device from a company that carries liability insurance for it.
That is not what this is.

## No warranty

This is provided under the MIT license, which means it comes with absolutely no
warranty of any kind. See [LICENSE](LICENSE). You are installing configuration
written for one specific house and adapting it to your own. You own the outcome.
