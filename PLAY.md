# Play Card Wars on your Mac

Works on any Mac: Apple Silicon (M1/M2/M3/M4) or Intel.

## Install (one command)

1. Open **Terminal**: press **⌘ Space**, type `Terminal` and press **Enter**.
2. Paste this line and press **Enter**:

   ```
   curl -fsSL https://raw.githubusercontent.com/adomjab/aseprite-builder/claude/cardwars-macos-compat-jeh7xi/cardwars-macos/install.sh | bash
   ```

3. If it asks for a password, type your Mac login password. Nothing shows on
   screen while you type; that's normal. Press **Enter**.

The installer sets up Rosetta (needed on M-series Macs), downloads the game,
puts it in **Applications** and opens it. After that, start it from Launchpad
or Spotlight like any other app.

## Install by hand

1. Download **CardWars-macOS.zip** from the
   [release page](https://github.com/adomjab/aseprite-builder/releases/tag/cardwars-macos).
2. Double-click the zip, then drag **CardWars** into **Applications**.
3. The first time, **right-click CardWars → Open → Open**. If macOS says it is
   "damaged" or "can't be opened", run this in Terminal:
   ```
   xattr -cr /Applications/CardWars.app
   ```
4. On an M-series Mac, click **Install** if macOS asks to install Rosetta.

## Good to know

- If the game says **"Server did not respond. Retry?"**, choose **No** to play
  offline as a guest. Your progress is still saved on your Mac.
- Progress is saved in `~/Library/Application Support/shishkabob/Card Wars/`.
  Reinstalling or updating the game doesn't touch it.
- To update, run the install command again.
