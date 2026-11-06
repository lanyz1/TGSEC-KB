## 18. Video Analysis

### 18.1 Context extraction

Signs/banners, architecture, road markings, license plates, clothing, cross-platform snippet search.

### 18.2 Metadata

YouTube Data Viewer (Amnesty), ExifTool on downloaded files.

### 18.3 Platform-specific

- **TikTok / Instagram** — APIs change often; prefer platform exports; sample 1–4h cadence.
- **Bluesky AT Protocol** — DID resolution via `bsky.social/xrpc/com.atproto.identity.resolveHandle`; identity doc via `plc.directory/<did>`; firehose at Firesky; SkyView for graphs. Archive early — handle migration / post deletion.
- **Mastodon / Fediverse** — instance matters (jurisdiction, logging); WebFinger for discovery; FediSearch cross-instance; instance enumeration via Fediverse Observer; ActivityPub objects are JSON-LD.
- **Threads** — IG-API-similar limitations.

### 18.4 Auditory clues

Languages, dialects, background noises (train horns, prayer calls, wildlife). Tools: Audacity, Sonic Visualiser, SoundCMD. Spectrograms for unique patterns; Shazam/SoundHound for music.

### 18.5 Frame extraction

FFmpeg, VLC. Stitch panoramas; stabilize panning footage (FFmpeg `deshake` or Blender VSE). Prefer original uploads over re-encodes.

---

