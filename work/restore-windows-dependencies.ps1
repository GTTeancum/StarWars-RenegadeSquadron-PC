param(
    [string]$Destination = $PSScriptRoot,
    [string]$ArchiveDirectory = (Join-Path $PSScriptRoot 'windows-deps')
)
$ErrorActionPreference = 'Stop'
$items = @(
    @{Name='ffmpeg-n7.1.5-12-g1fdbca85aa-win64-lgpl-shared-7.1.zip'; Hash='0f376f96fb38554ccefb1b2ae9c7c6a7b351f0e60a372b38262c320e8392c5d0'; Url='https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-07-31-14-10/ffmpeg-n7.1.5-12-g1fdbca85aa-win64-lgpl-shared-7.1.zip'},
    @{Name='SDL2-devel-2.32.10-VC.zip'; Hash='af347939395a58b365846aaea27391e69f9ec9d4dd650d6ac40802159b418a6e'; Url='https://github.com/libsdl-org/SDL/releases/download/release-2.32.10/SDL2-devel-2.32.10-VC.zip'}
)
New-Item -ItemType Directory -Force -Path $Destination,$ArchiveDirectory | Out-Null
$sdk = Join-Path $Destination 'windows-sdk'
if (Test-Path -LiteralPath $sdk) { throw "SDK already exists: $sdk. Choose a new destination to reproduce independently." }
$expanded = Join-Path $Destination 'dependency-expansion010'
if (Test-Path -LiteralPath $expanded) { throw "Expansion directory already exists: $expanded" }
foreach ($item in $items) {
    $archive = Join-Path $ArchiveDirectory $item.Name
    if (!(Test-Path -LiteralPath $archive)) { Invoke-WebRequest -Uri $item.Url -OutFile $archive }
    $actual = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $item.Hash) { throw "Dependency hash mismatch: $archive" }
    Expand-Archive -LiteralPath $archive -DestinationPath $expanded
}
$ff = Join-Path $expanded 'ffmpeg-n7.1.5-12-g1fdbca85aa-win64-lgpl-shared-7.1'
$sdl = Join-Path $expanded 'SDL2-2.32.10'
New-Item -ItemType Directory -Force -Path "$sdk/usr/include/SDL2","$sdk/lib","$sdk/bin" | Out-Null
Copy-Item "$ff/include/*" "$sdk/usr/include" -Recurse
Copy-Item "$ff/lib/*.lib" "$sdk/lib"
Copy-Item "$ff/bin/*.dll" "$sdk/bin"
Copy-Item "$sdl/include/*" "$sdk/usr/include/SDL2"
Copy-Item "$sdl/lib/x64/SDL2.lib" "$sdk/lib"
Copy-Item "$sdl/lib/x64/SDL2.dll" "$sdk/bin"
$records = Get-ChildItem -LiteralPath $sdk -File -Recurse | ForEach-Object {
    [pscustomobject]@{Path=[IO.Path]::GetRelativePath($sdk,$_.FullName).Replace('\','/');Size=$_.Length;SHA256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
}
$records | Sort-Object Path | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $Destination 'windows-sdk-sha256.json')
Write-Output "Verified dependency archives and restored $($records.Count) SDK files to $sdk"
