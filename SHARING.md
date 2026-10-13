# Sharing your build with friends

You build the game once, then upload it to GitHub as a Release. Friends then
follow [PLAY.md](PLAY.md) and never need Unity.

## 1. Package the app (on your Mac)

```
cd ~/aseprite-builder/cardwars-macos
git pull
./package.sh
```

This re-signs the app and creates `CardWars-macOS.zip` in the same folder.
It looks for the app in `CardWars/Builds/macOS/` first, then
`/Applications/`. To package a different copy, pass its path:
`./package.sh /path/to/CardWars.app`.

## 2. Upload it as a GitHub Release

1. Open https://github.com/adomjab/aseprite-builder/releases/new
2. **Choose a tag**: type `cardwars-macos` and click **Create new tag**.
   Use exactly this name, because the installer downloads from it.
3. **Target**: select the branch `claude/cardwars-macos-compat-jeh7xi`.
4. **Title**: e.g. `Card Wars for macOS`.
5. Drag `CardWars-macOS.zip` into the **Attach binaries** box and wait for the
   upload to finish. Files up to 2 GB are fine.
6. Click **Publish release**.

## 3. Send your friends the link

Send them the link to **PLAY.md**:
https://github.com/adomjab/aseprite-builder/blob/claude/cardwars-macos-compat-jeh7xi/cardwars-macos/PLAY.md

## Updating later

Rebuild, run `./package.sh` again, then edit the `cardwars-macos` release:
delete the old zip and upload the new one. Friends get the update by running
the install command again.

## Before you share

- **The repo must be public** for friends to download without a GitHub login.
  Releases of a private repo only work for people you add as collaborators.
- **Copyright:** the game's art and audio belong to Cartoon Network. Sharing
  with a few friends is low-key, but advertising it widely is riskier.
- **Your own server:** if you switch to your own server, change
  `server_settings.json` *before* packaging so friends connect to it too.
  See "Game server" in [README.md](README.md).
