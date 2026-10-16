# Card Wars on macOS (maintainer branch)

> This `dev` branch holds the build, packaging and server tools. The `main`
> branch only has what players need: the install guide and `install.sh`.
> Work here with `git checkout dev`.

**Just want to play?** See [PLAY.md](PLAY.md). To share your own build with
friends, see [SHARING.md](SHARING.md). To host your own game server, see
[SERVER.md](SERVER.md) (the server program itself is in [`server/`](server/)).

A patch for [shishkabob27/CardWars](https://github.com/shishkabob27/CardWars)
(Unity 2017.4.40f1) that lets you build and run it as a native macOS `.app`.

## What the patch changes

| File | Change | Why |
| --- | --- | --- |
| `ProjectSettings/ProjectSettings.asset` | Adds macOS graphics APIs (Metal, falling back to OpenGL Core) and a Standalone bundle id | The project only had Windows (D3D11) set up |
| `Assets/Resources/shaders/Unlit-Alpha-With-Fade2.shader` (+ `.meta`) | Rewrites this shader as normal Cg source | The original was a ripped, compiled **GLES-only** shader, so it can't run on Metal/OpenGL Core (or D3D) and draws nothing or pink |
| `Assets/Scripts/Assembly-CSharp/SQSettings.cs` | Wraps the iOS-only `[DllImport("__Internal")]` declarations in `#if UNITY_IOS` | They don't exist in a desktop player |
| `Assets/Scripts/Assembly-CSharp/SQContentPatcher.cs` | `Application.dataPath + Path.PathSeparator + name` → `Path.Combine(...)` | `PathSeparator` is `:` on macOS (`;` on Windows), so the path was wrong |
| `Assets/Scripts/Assembly-CSharp-firstpass/UIButtonPlayAnimation.cs` | Falls back to the `_0`-renamed clip when a target doesn't have the requested one | Restores the camera fly-in/out when opening chests: the chest's and camera's clips shared a name and one was renamed when the project was recovered |
| `Assets/Scripts/Assembly-CSharp/AIManager.cs` | Re-reads the opponent's lanes before every decision | The AI kept the lanes of the first battle setup; after the game reloaded (logging in, Options, reconnecting) it saw every lane as empty and played creatures and buildings on top of ones already in play ([issue #8](https://github.com/shishkabob27/CardWars/issues/8)) |
| `Assets/StreamingAssets/Blueprints/db_Leaders.json` | `Leader_Gunter_FC` uses character `Gunter` instead of the non-existent `Gunter02` | Fionna & Cake level 24 (quest 5039) crashed / went black after its cutscene |
| 56 prefabs and scenes (via `tools/fix_default_animations.py`) | Restores the default clip on 73 auto-playing Animation components that only have one clip | Recovering the project dropped these defaults, so nothing played: the chest "Nice/Rare/Very Rare/Algebraic Rare Card!" banners, "You Win/You Lose", hit/crit and spell effects, tombstones, animated scenery and menu idles |
| `Assets/Resources/props/FX_Battle_Spell_Volcano.prefab` (+ `low_` copy) | Makes `Volcano_anim` the clip that plays automatically | The recovered prefab played a 0.17 s flying-lava clip (or nothing), so the Volcano spell showed a still volcano without the rising volcano, lava flood or camera move |
| `Assets/Editor/MacBuild.cs` (new) | Adds **Card Wars > Build macOS** and **Card Wars > Build Windows** menu items and batch-mode build methods | One-step builds; `build.sh` and `build-windows.sh` use them |

The rest of the game code was already cross-platform. It has no native plugins,
and the Windows-only checks in it (NGUI's half-pixel offset for Direct3D 9) are
already right for macOS.

## Step by step on an M1 / Apple Silicon Mac

Unity 2017 and the game it builds are Intel apps, so on an M1 they run through
Rosetta 2. That works fine; you just need Rosetta installed.

1. Open Terminal and install the basics (skip any you already have):
   ```bash
   softwareupdate --install-rosetta --agree-to-license
   xcode-select --install
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
   git clone https://github.com/adomjab/cardwars-macos.git
   cd cardwars-macos
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

`setup.sh` clones CardWars into `./CardWars` and applies the patch;
`build.sh` builds `./CardWars/Builds/macOS/CardWars.app`.

```bash
cd cardwars-macos
./setup.sh
./build.sh
open CardWars/Builds/macOS/CardWars.app
```

You can also open `./CardWars` in Unity and choose **Card Wars > Build macOS**.
To build from Windows, install the "Mac Build Support" module for 2017.4.40f1
and use the same menu item.

### The Windows version, built on a Mac

The same patched project builds for Windows, so Windows players get the code
fixes too. Add the **Windows Build Support** module first: Unity Hub >
**Installs** > the **⋯** menu on 2017.4.40f1 > **Add modules** > tick
**Windows Build Support** > Install. Then:

```bash
./build-windows.sh
./package-windows.sh --server 35.229.126.223
```

This makes `CardWars-Windows.zip`. Upload it to the same release as
`CardWars-macOS.zip`; `install-windows.ps1` uses it when the latest release
has one. If the build fails, the details are in
`CardWars/Builds/build-windows.log`.

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

## Game server

The game talks to the community server set in
`Assets/StreamingAssets/server_settings.json` (`http://cardwars.retroretreat.net/`).
The Windows release uses the same server, so Mac players share accounts,
saves and multiplayer with Windows players. The official Cartoon Network
servers shut down in 2020.

The server is used for login, cloud saves, multiplayer, tournaments,
leaderboards and content updates. Your progress is also saved on your
computer, and when the server can't be reached the game keeps going without
cloud saving and shows "Connection" errors.

To use a different server without rebuilding, edit
`CardWars.app/Contents/Resources/Data/StreamingAssets/server_settings.json`,
then re-sign the app with `codesign --force --deep --sign - CardWars.app`.
