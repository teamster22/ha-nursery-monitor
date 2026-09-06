# Frigate setup

> Read [../DISCLAIMER.md](../DISCLAIMER.md) first. Short version: not a medical device, and an LLM
> wrote essentially all of the code here. I'm not a software engineer, so read the
> config yourself before you run it.

Merge [`nursery.yaml`](nursery.yaml) into your existing Frigate `config.yaml`.
Don't paste it over the whole file.

## Get the camera right first

The cry detection runs on the camera's **audio** stream, so audio has to exist and
has to be a codec Frigate can read. Mine shipped with audio disabled and H.265 video
on both streams, which is useless for this. In the camera's own web UI:

- **Audio:** enable on main and sub, codec **AAC**, sampling rate **16000**
- **Encode:** **H.264** on both. Main 2688x1520@15, sub 704x480 D1 @10. I-frame
  interval equal to frame rate (a 1 second GOP) on both.

Verify before you go further:

```bash
ffprobe -v error -show_streams "rtsp://user:pass@CAMERA_IP:554/cam/realmonitor?channel=1&subtype=1" \
  | grep -E 'codec_name|sample_rate|channels'
```

You want `h264` video and `aac` audio at `16000` Hz mono on **both** streams.

## The audio role goes on the sub stream

Both streams carry the same 16 kHz AAC, so analyzing the 768 kb/s sub costs far less
than the 4.8 Mb/s main. Frigate needs the `audio` role on *some* input or audio
detection silently never runs at all, which is a fun thirty minutes to spend.

## The label is `crying`

Not `crying_sobbing`, not `baby_cry_infant_cry`. Frigate collapses several YAMNet
infant-cry classes into the single label `crying`. Before you add any audio label,
check what actually exists:

```bash
docker exec frigate cat /audio-labelmap.txt | grep -i cry
```

## `hwaccel_args: []` is load-bearing

Within 25 minutes of adding this camera, the detect ffmpeg was crash-looping every
three minutes with hardware surface sync failures, taking the camera unavailable for
about 20 seconds each time. Software decode fixed it.

Frigate defaults `hwaccel_args` to `auto`, so **omitting** the key re-enables the
decoder that crashes. It has to be present and explicitly empty. On a 704x480 @ 10fps
detect stream the CPU cost is nothing.

## The go2rtc audio path

This is the part worth copying whether or not you're building a baby monitor.

WebRTC can't carry AAC. It handles OPUS, PCMU, and PCMA. So if your camera emits AAC
and you don't do anything about it, go2rtc spawns a **separate ffmpeg transcode for
every connecting viewer**. I measured three concurrent transcodes and a 2.24 second
WebRTC handshake, which showed up as choppy video and intermittent audio.

```yaml
nursery_kiosk:
  - ffmpeg:nursery_main#video=copy#audio=opus
```

That does the AAC to OPUS conversion once, persistently, shared by every viewer.
`video=copy` means no video re-encode, so the cost is negligible.

Things I ruled out before finding it, so you don't repeat the work: camera link
(30/30 pings, 1.46 ms average, 0.27 ms jitter), host load (1.46 of 16 cores), camera
health (zero errors in 45 minutes of logs).

**One source line, ffmpeg-wrapped, on purpose.** A bare `rtsp://` line is what
exposes the two-way talkback backchannel. This is a baby monitor. Audio flows from
the nursery to the viewer and never the reverse. Don't add a second bare-RTSP source
under that stream.

## Source the kiosk stream from main, not sub

The sub stream is anamorphic (704x480 storing 16:9) and advanced-camera-card
preserves source aspect ratio, so a sub-sourced card renders about 17% horizontally
squished. Took me longer to notice than I'd like to admit.

## Lock down the go2rtc API

go2rtc's API listens on `0.0.0.0:1984` with no authentication by default, and
`/api/streams` returns the full ffmpeg command lines. That includes your camera RTSP
passwords, in cleartext. If Frigate runs with `network_mode: host`, anything on your
LAN can read them.

```yaml
go2rtc:
  api:
    listen: "127.0.0.1:1984"
```

Frigate proxies the streams internally, so this costs you nothing.

## Track `baby`, not just `person`

A swaddled infant lying flat very often does not register as `person`. If your
detection model has a `baby` class, track it. Check your labelmap.

## What you get in Home Assistant

With the Frigate integration installed:

| Entity | What it does |
|---|---|
| `binary_sensor.nursery_crying` | the audio classifier. This is what fires the alert |
| `binary_sensor.nursery_person_occupancy` | an adult is in frame |
| `binary_sensor.nursery_crib_baby_occupancy` | the crib zone. Comes from the zone config |
| `camera.nursery` | the feed |

Entity names follow your camera name, so if you call the camera something else,
update the references in `packages/`.
