# Set up a free server for Card Wars

This guide gets you a free cloud server that friends can reach from any Wi-Fi.
The game still runs on each player's Mac. The server only runs the Card Wars
**server program** (accounts, saves, multiplayer), and every copy of the game
connects to it.

> **Status:** the server program is new and tested against the game's code,
> but not yet against the real game. Expect a round or two of fixes the first
> time you play on it.

Two free options are covered: **Google Cloud** (simpler, recommended) and
**Oracle Cloud** (more free data, harder setup). Do one of them, then the two
shared sections at the end.

Time needed: about 20–30 minutes. You need a credit or debit card for
verification. Within the free limits you aren't charged.

---

## Google Cloud setup

### G1 – Create the account
1. Go to https://console.cloud.google.com and sign in with a Google account.
2. Click **Try for free** and finish the sign-up, including the card.
   You get a $300 / 90-day trial; the free server described here is separate
   and stays free after the trial (see G6).
3. A project called **My First Project** is created for you. That's fine.

### G2 – Create the free server
1. In the search bar at the top, type **VM instances** and open it. If asked,
   click **Enable** (Compute Engine API) and wait about a minute.
2. Click **Create instance** and set:
   - **Name:** `cardwars-server`
   - **Region:** `us-central1` (Iowa), `us-west1` (Oregon) or `us-east1`
     (South Carolina). **Only these three are free.** Any zone is fine.
   - **Machine configuration:** series **E2**, machine type **e2-micro**
     (under *Shared-core*).
   - **OS and storage** → **Change**: operating system **Debian**, version
     **Debian 12**, boot disk type **Standard persistent disk**, size **30** GB
     → **Select**. The default "Balanced" disk is **not** free.
   - **Networking → Firewall:** tick **Allow HTTP traffic**.
3. Click **Create**. The cost estimate on the right may show a monthly price;
   the free allowance is subtracted on the bill.
4. When the green tick appears, copy the **External IP** from the list,
   e.g. `34.123.45.67`. This is your server's address.

### G3 – Open the server's terminal
In the VM list, click **SSH** next to `cardwars-server`. A terminal window
opens in your browser, already logged into the server. (Click **Authorize** if
asked.)

### G4 – Test it from another network
In that SSH window, start a throwaway test web server:

```
mkdir -p ~/test && echo "Card Wars server is reachable!" > ~/test/index.html
```
```
cd ~/test && sudo python3 -m http.server 80
```

On your **phone using mobile data with Wi-Fi off**, open
`http://34.123.45.67` (your IP). If you see **"Card Wars server is
reachable!"**, friends on any Wi-Fi will be able to reach your server.

Press **Ctrl+C** to stop the test.

If the page doesn't load:
- Check that you used `http://`, not `https://`.
- In the VM's **Edit** page, check that **Allow HTTP traffic** is ticked.

### G5 – Add a $1 budget alert
Search for **Budgets & alerts** → **Create budget** → amount **$1** → keep
the email alerts on → **Finish**. If anything ever starts costing money, you
get an email.

### G6 – Keep it free and running
- **When the 90-day trial ends**, Google stops your servers unless you
  **upgrade** the account (a banner/button in the console). The e2-micro stays
  free after upgrading; only things beyond the free limits are charged.
- **Free limits:** 1 e2-micro in the three US regions, 30 GB standard disk,
  and **1 GB of outgoing data per month**. Card Wars traffic is small, but with
  several active players you could go a little over; extra data costs cents.
- **Don't stop the VM** if you can avoid it: the external IP can change after
  a stop/start, and then the game would need the new address. Rebooting is
  fine.
- **Don't add** bigger machines, extra disks, snapshots or other paid
  services.

---

## Oracle Cloud setup (alternative)

More free data (10 TB/month) and a region of your choice, but a harder setup.

### O1 – Create an Oracle Cloud account

1. Go to https://signup.cloud.oracle.com and sign up.
2. **Home region:** pick one close to you, such as *Germany Central
   (Frankfurt)* or *Sweden Central (Stockholm)*. **It can't be changed later**,
   and free servers can only be created in it.
3. Add your card. Oracle may place a small temporary hold to verify it.
4. Wait for the "account is ready" email (usually a few minutes, sometimes
   longer), then sign in at https://cloud.oracle.com.

### O2 – Create the free server

1. Open the menu ☰ → **Compute** → **Instances** → **Create instance**.
2. **Name:** `cardwars-server`
3. **Image and shape** → **Edit**:
   - **Image** → **Change image** → **Canonical Ubuntu**, newest version
     (e.g. 24.04) → **Select image**.
   - **Shape** → **Change shape**. Use either of these:
     - **Ampere** → `VM.Standard.A1.Flex` with **1 OCPU** and **6 GB** memory
       (the faster option), or
     - **Specialty and previous generation** → `VM.Standard.E2.1.Micro`
       (weaker, but easier to get).

     Both must show the **"Always Free-eligible"** label. If A1 says *Out of
     capacity*, use E2.1.Micro instead. It's enough for this game.
4. **Networking:** keep "Create new virtual cloud network" and make sure
   **Assign a public IPv4 address** is on.
5. **Add SSH keys:** choose **Generate a key pair for me** and click **Save
   private key**. Keep that file safe: it's your only way to log into the server.
6. **Boot volume:** leave the defaults.
7. Click **Create**. When the state turns green (**Running**), copy the
   **Public IP address**, e.g. `141.145.12.34`. This is your server's address.

### O3 – Open port 80 (two firewalls)

Port 80 is the standard web port, and the game connects to it. On Oracle you
have to open it in **two** places. Missing the second one is the most common
reason it "doesn't connect".

#### O3a. Oracle's firewall (Security List)

1. On your instance page, click the **subnet** link (under *Primary VNIC*).
2. Open **Security** (or **Security Lists**) → **Default Security List for …**
3. **Add Ingress Rules**:
   - **Source CIDR:** `0.0.0.0/0`
   - **IP Protocol:** TCP
   - **Destination Port Range:** `80`
4. Click **Add Ingress Rules**.

#### O3b. The server's own firewall

First log in from your Mac's Terminal. Replace the file name and IP with yours:

```
chmod 400 ~/Downloads/ssh-key-*.key
```
```
ssh -i ~/Downloads/ssh-key-*.key ubuntu@141.145.12.34
```

Type `yes` if asked. You're now on the server; the prompt changes to
`ubuntu@cardwars-server`. Run these two commands there:

```
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
```
```
sudo netfilter-persistent save
```

### O4 – Test it from another network

Still logged into the server, start a throwaway test web server:

```
mkdir -p ~/test && echo "Card Wars server is reachable!" > ~/test/index.html
```
```
cd ~/test && sudo python3 -m http.server 80
```

Now, on your **phone using mobile data with Wi-Fi off**, open
`http://141.145.12.34` (your IP). If you see **"Card Wars server is
reachable!"**, the server works from any network, and friends on other Wi-Fis
will be able to reach it too.

Press **Ctrl+C** in Terminal to stop the test. Type `exit` to log out.

If the page doesn't load:
- Check that you used `http://`, not `https://`.
- Re-check the ingress rule in O3a (port 80, TCP, `0.0.0.0/0`).
- Re-run the two commands in O3b.

### O5 – Keep it free and keep it alive

- **Idle servers can be reclaimed.** Oracle may take back Always Free servers
  that stay mostly idle (under 20% CPU, network and memory use) for 7 days, and
  a small game server is usually that quiet. To prevent it, upgrade the account
  to **Pay As You Go**: ☰ → **Billing & Cost Management** → **Upgrade and
  Manage Payment**. Always Free resources stay free after upgrading; only
  usage beyond the free limits is charged.
- **Add a budget alert** so you're warned if anything ever costs money:
  ☰ → **Billing & Cost Management** → **Budgets** → **Create Budget**, amount
  `1`, with an email alert.
- **Only create "Always Free-eligible" things.** Bigger shapes, extra disks
  or backups cost money once you're on Pay As You Go.
- **Keep the same IP:** the public IP stays as long as you don't delete the
  instance. Restarting it is fine.

---

## Install the Card Wars server program

In the server's terminal (Google: the **SSH** button; Oracle: `ssh` from your
Mac), paste:

```
curl -fsSL https://raw.githubusercontent.com/adomjab/cardwars-macos/dev/server/install.sh | sudo bash
```

It installs the server, starts it on port 80 and makes it start again
automatically after a reboot. When it finishes it prints
**"Card Wars server is running!"** and, on Google Cloud, the address to use.

Check it from your phone (Wi-Fi off): `http://YOUR-IP/` should show
**"Card Wars server is running."**

Useful commands on the server:

| What | Command |
| --- | --- |
| Is it running? | `sudo systemctl status cardwars` |
| Watch live activity | `sudo journalctl -u cardwars -f` (Ctrl+C to stop) |
| Restart it | `sudo systemctl restart cardwars` |
| Update to the newest version | run the install command again |
| Back up all accounts and saves | `sudo cp /var/lib/cardwars/cardwars.db ~/cardwars-backup.db` |

What it does: accounts, cloud saves, multiplayer (you fight other players'
saved decks), leaderboards and weekly tournaments (ending Monday 00:00 UTC,
cycling through the game's 216 tournaments and their prizes). While you're the
only player with a Deck Wars deck, you practice against a copy of your own
deck. In-app purchases are switched off.

## Point the game at your server

On your Mac, before packaging the game for friends:

1. Edit `CardWars/Assets/StreamingAssets/server_settings.json` so it reads
   (with your IP, keeping `http://` and the final `/`):
   ```json
   {
       "type" : "server_settings",
       "server_url" : "http://141.145.12.34/"
   }
   ```
2. Rebuild with `./build.sh`, then `./package.sh`, and publish a new release
   (see [SHARING.md](SHARING.md)).

To change an already built app instead, edit
`CardWars.app/Contents/Resources/Data/StreamingAssets/server_settings.json`
and re-sign it with `codesign --force --deep --sign - CardWars.app`.

## Logging in (each player)

- **New players:** at the login screen, type a username (3–24 letters,
  numbers, `.`, `-` or `_`) and a password. If the name is free, the game
  offers to create the account.
- **Players who were playing as a guest:** the login screen only shows the
  first time. To get it back, quit the game and run this in Terminal (it
  resets the game's settings, **not** your progress):
  ```
  defaults delete "unity.shishkabob.Card Wars"
  ```
  Then start the game and log in. Your guest progress is copied into the new
  account. (Back up your save first, just in case:
  `cp -R ~/Library/Application\ Support/shishkabob/Card\ Wars ~/Desktop/CardWars-save-backup`)
- Use a password you don't use anywhere else: the game sends it without
  encryption (plain `http://`).

## Event reminders and announcements

When players log in, the game can show a message pop-up. The server uses it
for two things:

- **Event reminders (automatic).** In the 24 hours before each carnival
  (Halloween Festival, Rare Card Carnival, ...) and before the Halloween and
  Christmas months, logged-in players see a reminder once. The server reads
  the schedule from the repo's `gamedata` folder and refreshes it every 6
  hours, so it always matches what the installers give players.
- **Your own announcements.** Create `/var/lib/cardwars/announcements.json` on
  the server:
  ```
  sudo nano /var/lib/cardwars/announcements.json
  ```
  ```json
  [
    {
      "id": "welcome-2026",
      "message": "Welcome to our Card Wars server! Here are some coins to get you started.",
      "coins": 10000,
      "gems": 5,
      "start": "2026-10-20",
      "end": "2026-11-20"
    }
  ]
  ```
  Each player sees each announcement once, the next time they log in between
  `start` and `end` (dates in UTC; `"2026-10-20T18:00"` also works). `coins`
  and `gems` are optional gifts, added when the player taps OK. Give every
  announcement a new `id`; reusing an `id` won't show it again to people who
  already saw it. Changes apply immediately, no restart needed.

Guests (not logged in) don't get messages.
