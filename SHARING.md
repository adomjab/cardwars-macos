# Sharing your build with friends

You build the game once, then upload it to GitHub as a Release. Friends then
follow [PLAY.md](PLAY.md) and never need Unity.

## 1. Package the app (on your Mac)

```
cd ~/cardwars-macos
git checkout dev
git pull
./package.sh --server 35.229.126.223
```

`--server` sets the game server inside the app, so everyone who downloads it
is connected to your server automatically. The script then re-signs the app
and creates `CardWars-macOS.zip` in the same folder. (Leave `--server` out to
keep whatever server the app already has; the script always prints it.)
It looks for the app in `CardWars/Builds/macOS/` first, then
`/Applications/`. To package a different copy, pass its path:
`./package.sh /path/to/CardWars.app`.

## 2. Upload it as a GitHub Release

1. Open https://github.com/adomjab/cardwars-macos/releases/new
2. **Choose a tag**: type a version such as `v1` and click **Create new tag**.
3. **Target**: leave it on `main`.
4. **Title**: e.g. `Card Wars for macOS`.
5. Drag `CardWars-macOS.zip` into the **Attach binaries** box and wait for the
   upload to finish. Files up to 2 GB are fine.
6. Click **Publish release**.

## 3. Send your friends the link

Send them the link to **PLAY.md**:
https://github.com/adomjab/cardwars-macos

## Updating later

Rebuild, run `./package.sh` again, and publish a new release (e.g. `v2`)
with the new zip. The installer always downloads the latest release. Friends get the update by running
the install command again.

## Before you share

- **The repo must be public** for friends to download without a GitHub login.
  Releases of a private repo only work for people you add as collaborators.
- **Copyright:** the game's art and audio belong to Cartoon Network. Sharing
  with a few friends is low-key, but advertising it widely is riskier.
- **Your own server:** if you switch to your own server, change
  `server_settings.json` *before* packaging so friends connect to it too.
  See "Game server" in [README.md](README.md).
