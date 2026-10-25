<#
.SYNOPSIS
  Publish a FairyGUI package with ofgui, applying patches and loading 996Extend Lua plugin.

.DESCRIPTION
  1. Run patch_ofgui.py on the given ofgui install (idempotent).
  2. Set OFGUI_ITEM_PATH / OFGUI_ITEMEQUIP_PATH env vars for the Lua plugin.
  3. Call ofgui publish for a single package.

  This is a global skill script; it does not assume the repo location.
  Defaults repo root to the current working directory; override with -Repo.
  The repo must contain tools/ofgui_patch/patch_ofgui.py.

.PARAMETER OfguiNodeModules
  node_modules directory containing @openfairygui/cli and fengari.

.PARAMETER Repo
  Repository root. Defaults to current working directory.

.PARAMETER Project
  FGUI project root (with .fairy file). Defaults to <Repo>/9963d_rxjh_fgui_project.

.PARAMETER Package
  Package name to publish, e.g. Bag, ItemIcon.

.PARAMETER Output
  Output directory.

.PARAMETER ItemConfigDir
  Directory containing Item.lua / ItemEquip.lua.
  Defaults to <Repo>/client/rjengineb_Data/StreamingAssets/Bundles/dev/Lua/game_config.

.EXAMPLE
  .\publish.ps1 -OfguiNodeModules D:\tools\ofgui\node_modules -Package Bag -Output D:\publish\Bag
#>
param(
    [Parameter(Mandatory = $true)] [string] $OfguiNodeModules,
    [string] $Repo,
    [string] $Project,
    [Parameter(Mandatory = $true)] [string] $Package,
    [Parameter(Mandatory = $true)] [string] $Output,
    [string] $ItemConfigDir
)

$ErrorActionPreference = "Stop"

if (-not $Repo) { $Repo = $PWD.Path }
$patchScript = Join-Path $PSScriptRoot "patch_ofgui.py"
if (-not (Test-Path -LiteralPath $patchScript)) {
    throw "Patch script not found: $patchScript"
}

if (-not $Project) {
    $Project = Join-Path $Repo "9963d_rxjh_fgui_project"
}
if (-not $ItemConfigDir) {
    $ItemConfigDir = Join-Path $Repo "client\rjengineb_Data\StreamingAssets\Bundles\dev\Lua\game_config"
}

Write-Host "==> patching ofgui (repo: $Repo)"
Write-Host "    ofgui: $OfguiNodeModules"
python $patchScript $OfguiNodeModules
if ($LASTEXITCODE -ne 0) { throw "patch failed" }

Write-Host "==> setting plugin env vars"
$env:OFGUI_ITEM_PATH = Join-Path $ItemConfigDir "Item"
$env:OFGUI_ITEMEQUIP_PATH = Join-Path $ItemConfigDir "ItemEquip"
Write-Host "    OFGUI_ITEM_PATH      = $env:OFGUI_ITEM_PATH"
Write-Host "    OFGUI_ITEMEQUIP_PATH = $env:OFGUI_ITEMEQUIP_PATH"

Write-Host "==> publishing package: $Package"
$cli = Join-Path $OfguiNodeModules "@openfairygui\cli\bin\cli.cjs"
node $cli publish $Project -p $Package -o $Output
if ($LASTEXITCODE -ne 0) { throw "publish failed" }

Write-Host "==> done. output: $Output"
