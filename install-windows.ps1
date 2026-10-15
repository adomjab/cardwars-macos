# One-line installer for Card Wars on Windows. Players run in PowerShell:
#   irm https://raw.githubusercontent.com/adomjab/cardwars-macos/main/install-windows.ps1 | iex
#
# Downloads the official Windows build from shishkabob27/CardWars, points it at
# our game server, and adds Desktop and Start Menu shortcuts. Running it again
# updates the game; saves are kept (they live outside the game folder).

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # the progress bar makes downloads very slow
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Server  = 'http://35.229.126.223/'
$ZipUrl  = 'https://github.com/shishkabob27/CardWars/releases/latest/download/CardWars-Windows.zip'
$DataUrl = 'https://raw.githubusercontent.com/adomjab/cardwars-macos/main/gamedata'
$Dest    = if ($env:CARDWARS_INSTALL_DIR) { $env:CARDWARS_INSTALL_DIR } else { Join-Path $env:LOCALAPPDATA 'CardWars' }
$GameDir = Join-Path $Dest 'game'
$Work    = Join-Path ([IO.Path]::GetTempPath()) ('cardwars-' + [Guid]::NewGuid().ToString('N'))

function Write-Step($text) { Write-Host "==> $text" -ForegroundColor Cyan }

function Set-ServerSettings($path) {
    $json = "{`n    `"type`" : `"server_settings`",`n    `"server_url`" : `"$Server`"`n}`n"
    # No byte-order mark: the game's JSON reader doesn't expect one.
    [IO.File]::WriteAllText($path, $json, (New-Object Text.UTF8Encoding($false)))
}

Write-Host 'Card Wars for Windows installer' -ForegroundColor Green

if (Get-Process -Name 'CardWars' -ErrorAction SilentlyContinue) {
    Write-Host 'Card Wars is running. Close it and run the installer again.' -ForegroundColor Yellow
    return
}

New-Item -ItemType Directory -Force -Path $Work | Out-Null
try {
    $zip = Join-Path $Work 'CardWars-Windows.zip'
    if ($env:CARDWARS_ZIP) {
        Copy-Item $env:CARDWARS_ZIP $zip
    } else {
        Write-Step 'Downloading the game (about 280 MB, this can take a few minutes)...'
        Invoke-WebRequest -Uri $ZipUrl -OutFile $zip -UseBasicParsing
    }

    Write-Step 'Unpacking...'
    $unpacked = Join-Path $Work 'unpacked'
    Expand-Archive -Path $zip -DestinationPath $unpacked -Force

    # The zip contains an updater (CardWars\CardWars.exe) and the real game in
    # CardWars\game. We install only the game: the updater talks to the old
    # server and could put the old server address back.
    $exe = Get-ChildItem -Path $unpacked -Recurse -Filter 'CardWars.exe' |
        Where-Object { Test-Path (Join-Path $_.DirectoryName 'CardWars_Data') } |
        Select-Object -First 1
    if (-not $exe) { throw 'Could not find the game inside the download.' }

    Write-Step "Installing to $GameDir"
    if (Test-Path $GameDir) { Remove-Item -Recurse -Force $GameDir }
    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    Move-Item -Path $exe.DirectoryName -Destination $GameDir

    Write-Step "Connecting the game to $Server"
    Set-ServerSettings (Join-Path $GameDir 'CardWars_Data\StreamingAssets\server_settings.json')
    # The game prefers a downloaded copy of the settings if one exists.
    if ($env:USERPROFILE) {
        $override = Join-Path $env:USERPROFILE 'AppData\LocalLow\shishkabob\Card Wars\Contents\server_settings.json'
        if (Test-Path $override) { Set-ServerSettings $override }
    }

    # Shared game data: yearly event schedules (the game's own ended in 2025)
    # and the gem prices, so Mac and Windows players get the same.
    Write-Step 'Adding events, gem prices and fixes...'
    $blueprints = Join-Path $GameDir 'CardWars_Data\StreamingAssets\Blueprints'
    foreach ($f in 'db_Schedule.json', 'db_GachaSchedule.json', 'db_IAP.json', 'db_Leaders.json') {
        $target = Join-Path $blueprints $f
        if ($env:CARDWARS_DATA_DIR) {
            Copy-Item (Join-Path $env:CARDWARS_DATA_DIR $f) $target -Force
        } else {
            Invoke-WebRequest -Uri "$DataUrl/$f" -OutFile $target -UseBasicParsing
        }
        # A copy downloaded by the old server's content updates would win; remove it.
        if ($env:USERPROFILE) {
            $old = Join-Path $env:USERPROFILE "AppData\LocalLow\shishkabob\Card Wars\Contents\Blueprints\$f"
            if (Test-Path $old) { Remove-Item -Force $old }
        }
    }

    $gameExe = Join-Path $GameDir 'CardWars.exe'
    try {
        Write-Step 'Adding shortcuts...'
        $shell = New-Object -ComObject WScript.Shell
        $places = @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))
        foreach ($place in $places) {
            if (-not $place) { continue }
            $lnk = $shell.CreateShortcut((Join-Path $place 'Card Wars.lnk'))
            $lnk.TargetPath = $gameExe
            $lnk.WorkingDirectory = $GameDir
            $lnk.IconLocation = "$gameExe,0"
            $lnk.Save()
        }
    } catch {
        Write-Host "Couldn't create shortcuts; start the game from $gameExe" -ForegroundColor Yellow
    }

    Write-Host ''
    Write-Host 'Done! Card Wars is installed. Use the "Card Wars" shortcut on your Desktop.' -ForegroundColor Green
    if (-not $env:CARDWARS_NO_LAUNCH) { Start-Process -FilePath $gameExe -WorkingDirectory $GameDir }
}
finally {
    Remove-Item -Recurse -Force $Work -ErrorAction SilentlyContinue
}
