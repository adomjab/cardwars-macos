# Card Wars for Mac and Windows

Adventure Time: Card Wars on your computer, with online accounts and
multiplayer. Mac and Windows players share the same server, so you can play
against each other.

- [Install on a Mac](#install-on-a-mac)
- [Install on Windows](#install-on-windows)
- [Logging in](#logging-in)
- [Event reminders](#event-reminders)

## Install on a Mac

Works on any Mac: Apple Silicon (M1/M2/M3/M4) or Intel.

1. Open **Terminal**: press **⌘ Space**, type `Terminal` and press **Enter**.
2. Paste this line and press **Enter**:

   ```
   curl -fsSL https://raw.githubusercontent.com/adomjab/cardwars-macos/main/install.sh | bash
   ```

3. If it asks for a password, type your Mac login password. Nothing shows on
   screen while you type; that's normal. Press **Enter**.

The installer sets up Rosetta (needed on M-series Macs), downloads the game,
puts it in **Applications** and opens it. After that, start it from Launchpad
or Spotlight like any other app.

<details>
<summary>Install by hand instead</summary>

1. Download **CardWars-macOS.zip** from the
   [release page](https://github.com/adomjab/cardwars-macos/releases/latest).
2. Double-click the zip, then drag **CardWars** into **Applications**.
3. The first time, **right-click CardWars → Open → Open**. If macOS says it is
   "damaged" or "can't be opened", run this in Terminal:
   ```
   xattr -cr /Applications/CardWars.app
   ```
4. On an M-series Mac, click **Install** if macOS asks to install Rosetta.

</details>

## Install on Windows

1. Open **PowerShell**: press the **Windows key**, type `PowerShell` and press
   **Enter**.
2. Paste this line and press **Enter**:

   ```
   irm https://raw.githubusercontent.com/adomjab/cardwars-macos/main/install-windows.ps1 | iex
   ```

The installer downloads the game (about 280 MB), connects it to our server,
adds a **Card Wars** shortcut to your Desktop and Start menu, and opens the
game. Always start the game with that shortcut.

## Logging in

At the login screen, enter a username and password. If the name is new, the
game offers to create an account, which keeps your progress on the server and
lets you play multiplayer. Use a password you don't use anywhere else: the game
sends it without encryption.

**Already playing as a guest?** The login screen only appears the first time.
To get it back, close the game, run the command below, and start the game
again. This resets the game's settings only; your progress is kept and moves
into the new account.

- Mac (Terminal): `defaults delete "unity.shishkabob.Card Wars"`
- Windows (PowerShell): `Remove-Item -Recurse "HKCU:\Software\shishkabob\Card Wars"`

## Event reminders

**In the game:** when you're logged in, a pop-up reminds you the day before
each carnival (Halloween Festival, Rare Card Carnival, ...) and before the
Halloween and Christmas months.

**On your phone or computer:** subscribe to the event calendar and you'll get
a notification one day before every event, even when the game is closed. It
updates itself when the schedule changes.

Calendar link:
`https://raw.githubusercontent.com/adomjab/cardwars-macos/main/gamedata/CardWars-events.ics`

- **iPhone:** Settings → Apps → Calendar → Calendar Accounts → Add Account →
  Other → **Add Subscribed Calendar**, paste the link, tap Next, then make sure
  **Remove Alerts is off** and tap Save.
- **Mac:** Calendar app → File → **New Calendar Subscription**, paste the
  link, and untick **Remove: Alerts**.
- **Google Calendar** (computer): next to "Other calendars" click **+ → From
  URL** and paste the link. Google ignores the built-in reminders, so open the
  calendar's settings and add an event notification **1 day before**.

## Good to know

- If the game says **"Server did not respond. Retry?"**, choose **No** to play
  offline as a guest. Your progress is still saved on your computer.
- Progress is saved here, and reinstalling or updating the game doesn't touch
  it:
  - Mac: `~/Library/Application Support/shishkabob/Card Wars/`
  - Windows: `%USERPROFILE%\AppData\LocalLow\shishkabob\Card Wars\`
- To update, run the install command again.
- **Events** (Halloween and Christmas battles and themes, monthly login
  calendar, special card packs) repeat every year, and **gems cost the same on
  Mac and Windows** (bought with coins: 500 coins for 1 gem, down to 12,000
  coins for 36). The installers add these from the [`gamedata`](gamedata/)
  folder, along with a fix for the Fionna & Cake **level 24** crash, and
  Lumpy Space Princess and Prince battles play LSP's own music.
- **Special offers:** now and then the main menu or the chests screen offers
  one of the original card packs (Halloween and Christmas packs in season),
  paid with gems instead of real money. At most one offer per screen a day.
- **Cards have their original stats** from the mobile game (attack, defense,
  costs, floop costs and abilities), not the 2023 rebalance in the PC port. If you installed
  before they were added, run the install command again.

## Credits

Based on [shishkabob27/CardWars](https://github.com/shishkabob27/CardWars), the
PC port of the mobile game. Card Wars and Adventure Time belong to Cartoon
Network. This is an unofficial fan project.
