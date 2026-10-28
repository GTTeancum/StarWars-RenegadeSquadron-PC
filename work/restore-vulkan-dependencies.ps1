$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$local = Join-Path $root '.local'
New-Item -ItemType Directory -Force -Path $local,(Join-Path $local 'temp') | Out-Null
$env:TEMP = Join-Path $local 'temp'
$env:TMP = $env:TEMP
$items = @(
    @{Archive='vulkan-headers.zip';Url='https://codeload.github.com/KhronosGroup/Vulkan-Headers/zip/19725e4d48082fe78e26622b15d3080ccd54112b';Hash='fc27464dff73c915ff509d50fbdab7dad2c752549a229e4cfb0bd218a7403cc1';Destination='Vulkan-Headers'},
    @{Archive='dxc.zip';Url='https://github.com/microsoft/DirectXShaderCompiler/releases/download/v1.9.2609/dxc_2026_09_29.zip';Hash='ad31b1fc8443175d204f77a611fdb3ef2ec42759bdc2f1167368de24a4a7e7f1';Destination='dxc'}
)
foreach ($item in $items) {
    $archive = Join-Path $local $item.Archive
    if (!(Test-Path -LiteralPath $archive)) { Invoke-WebRequest $item.Url -OutFile $archive }
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item.Hash) { throw "Checksum mismatch: $archive" }
    $destination = Join-Path $local $item.Destination
    if (Test-Path -LiteralPath $destination) { Write-Host "Using existing $destination"; continue }
    if ($item.Destination -eq 'Vulkan-Headers') {
        $expansion = Join-Path $local 'vulkan-headers-expansion'
        Expand-Archive -LiteralPath $archive -DestinationPath $expansion
        Move-Item -LiteralPath (Join-Path $expansion 'Vulkan-Headers-19725e4d48082fe78e26622b15d3080ccd54112b') -Destination $destination
    } else { Expand-Archive -LiteralPath $archive -DestinationPath $destination }
}
Write-Host 'Vulkan build dependencies ready inside the repository. Players only need their GPU driver.'
