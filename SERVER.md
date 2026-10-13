# Set up a free server for Card Wars

This guide gets you a free cloud server that friends can reach from any Wi-Fi.
The game still runs on each player's Mac. The server only runs the Card Wars
**server program** (accounts, saves, multiplayer), and every copy of the game
connects to it.

> **Status:** the Card Wars server program isn't written yet. Parts 1–4 set up
> and test the server so it's ready; part 5 is where the program goes once it
> exists.

Time needed: about 30–45 minutes. You need a credit or debit card for
verification. Within the free limits you aren't charged.

---

## Part 1 – Create an Oracle Cloud account

1. Go to https://signup.cloud.oracle.com and sign up.
2. **Home region:** pick one close to you, such as *Germany Central
   (Frankfurt)* or *Sweden Central (Stockholm)*. **It can't be changed later**,
   and free servers can only be created in it.
3. Add your card. Oracle may place a small temporary hold to verify it.
4. Wait for the "account is ready" email (usually a few minutes, sometimes
   longer), then sign in at https://cloud.oracle.com.

## Part 2 – Create the free server

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

## Part 3 – Open port 80 (two firewalls)

Port 80 is the standard web port, and the game connects to it. On Oracle you
have to open it in **two** places. Missing the second one is the most common
reason it "doesn't connect".

### 3a. Oracle's firewall (Security List)

1. On your instance page, click the **subnet** link (under *Primary VNIC*).
2. Open **Security** (or **Security Lists**) → **Default Security List for …**
3. **Add Ingress Rules**:
   - **Source CIDR:** `0.0.0.0/0`
   - **IP Protocol:** TCP
   - **Destination Port Range:** `80`
4. Click **Add Ingress Rules**.

### 3b. The server's own firewall

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

## Part 4 – Test it from another network

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
- Re-check the ingress rule in 3a (port 80, TCP, `0.0.0.0/0`).
- Re-run the two commands in 3b.

## Part 5 – Install the Card Wars server program

*Not available yet.* When it's ready, this part will be a couple of commands
that install it and keep it running on port 80, including after the server
restarts.

## Part 6 – Point the game at your server

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

## Part 7 – Keep it free and keep it alive

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

## Alternative: Google Cloud (simpler, US-only)

If Oracle has no capacity or you'd rather keep it simple, Google's free
`e2-micro` works too:

1. Sign up at https://console.cloud.google.com (the $300 trial; the free
   e2-micro continues after it if you upgrade the account when the trial ends).
2. **Compute Engine → VM instances → Create instance**:
   - Region **us-central1**, **us-west1** or **us-east1** (only these are free).
   - Machine type **e2-micro**.
   - Boot disk: **Debian 12**, disk type **Standard persistent disk**, 30 GB.
     The default "Balanced" disk is *not* free.
   - Firewall: tick **Allow HTTP traffic**. That's the only firewall step
     on Google.
3. Copy the **External IP**, click **SSH** to open a terminal in your browser,
   then do Part 4 (the test), skipping the `iptables` commands.
4. Add a $1 budget alert under **Billing → Budgets & alerts**.
