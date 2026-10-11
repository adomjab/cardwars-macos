# Card Wars on macOS

A patch for [shishkabob27/CardWars](https://github.com/shishkabob27/CardWars)
(Unity 2017.4.40f1) that lets you build and run it as a native macOS `.app`.

## What the patch changes

| File | Change | Why |
| --- | --- | --- |
| `ProjectSettings/ProjectSettings.asset` | Adds macOS graphics APIs (Metal, falling back to OpenGL Core) and a Standalone bundle id | The project only had Windows (D3D11) set up |
| `Assets/Resources/shaders/Unlit-Alpha-With-Fade2.shader` (+ `.meta`) | Rewrites this shader as normal Cg source | The original was a ripped, compiled **GLES-only** shader, so it can't run on Metal/OpenGL Core (or D3D) and draws nothing or pink |
| `Assets/Scripts/Assembly-CSharp/SQSettings.cs` | Wraps the iOS-only `[DllImport("__Internal")]` declarations in `#if UNITY_IOS` | They don't exist in a desktop player |
| `Assets/Scripts/Assembly-CSharp/SQContentPatcher.cs` | `Application.dataPath + Path.PathSeparator + name` → `Path.Combine(...)` | `PathSeparator` is `:` on macOS (`;` on Windows), so the path was wrong |
| `Assets/Editor/MacBuild.cs` (new) | Adds a **Card Wars > Build macOS** menu item and a batch-mode build method | A one-step macOS build |

The rest of the game code was already cross-platform. It has no native plugins,
and the Windows-only checks in it (NGUI's half-pixel offset for Direct3D 9) are
already right for macOS.

## Step by step on an M1 / Apple Silicon Mac

Unity 2017 and the game it builds are Intel apps, so on an M1 they run through
Rosetta 2. That works fine; you just need Rosetta installed.

1. Open Terminal and install the basics (skip any you already have):
   ```bash
   softwareupdate --install-rosetta --agree-to-license   # Intel app support
   xcode-select --install                                # git + codesign
   ```
2. Install [Unity Hub](https://unity.com/download), sign in, and activate a
   free Personal license (Hub > Settings > Licenses).
3. Install Unity **2017.4.40f1**. Paste `unityhub://2017.4.40f1/6e14067f8a9a`
   into Safari's address bar to open it in Hub. Hub installs the Intel editor
   automatically, because no Apple Silicon build exists for 2017.
4. Get this folder and run the scripts. CardWars is about 1.5 GB to download,
   and the first build takes a while because Unity imports every asset under
   Rosetta.
   ```bash
   git clone -b claude/cardwars-macos-compat-jeh7xi https://github.com/adomjab/aseprite-builder.git
   cd aseprite-builder/cardwars-macos
   ./setup.sh
   ./build.sh
   open CardWars/Builds/macOS/CardWars.app
   ```
   `build.sh` detects the M1, checks for Rosetta and runs Unity under it.
   If the build fails, the details are in `CardWars/Builds/build-macos.log`.

## Build it (any Mac)

You need a Mac with **Unity 2017.4.40f1**. In Unity Hub, open
`unityhub://2017.4.40f1/6e14067f8a9a` or use the
[Unity download archive](https://unity.com/releases/editor/archive). Mac build
support is built into the Mac editor.

```bash
cd cardwars-macos
./setup.sh            # clones CardWars into ./CardWars and applies the patch
./build.sh            # builds ./CardWars/Builds/macOS/CardWars.app
open CardWars/Builds/macOS/CardWars.app
```

You can also open `./CardWars` in Unity and choose **Card Wars > Build macOS**.
To build from Windows, install the "Mac Build Support" module for 2017.4.40f1
and use the same menu item.

## Notes

- Unity 2017.4 builds Intel (x86_64) apps. On Apple Silicon Macs they run
  through Rosetta 2, and an M1 has plenty of power for this game even with the
  translation.
- `build.sh` ad-hoc signs the app. If you copy the app to another Mac and
  macOS says it is "damaged", run `xattr -cr CardWars.app`, or right-click the
  app and choose **Open**.
- If graphics glitch on Metal, launch with OpenGL instead:
  `open CardWars.app --args -force-glcore`.
- Save data goes in `~/Library/Application Support/shishkabob/Card Wars/`.
