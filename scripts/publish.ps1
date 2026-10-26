<#
.SYNOPSIS
  Publish a FairyGUI package with ofgui (patch + env + publish).

.PARAMETER OfguiNodeModules
  node_modules with @openfairygui/cli and fengari.
.PARAMETER Repo
  Repo root (defaults to PWD).
.PARAMETER Project
  FGUI project root (defaults to <Repo>/9963d_rxjh_fgui_project).
.PARAMETER Package
  Package name, e.g. Bag.
.PARAMETER Output
  Output directory.
.PARAMETER ItemConfigDir
  Item.lua / ItemEquip.lua dir.
  Defaults to <Repo>/client/.../game_config.

.EXAMPLE
  .\publish.ps1 -OfguiNodeModules D:\tools\ofgui\node_modules -Package Bag -Output D:\publish\Bag
#>
param(
    [Parameter(Mandatory=$true)][string] $OfguiNodeModules,
    [string] $Repo,
    [string] $Project,
    [Parameter(Mandatory=$true)][string] $Package,
    [Parameter(Mandatory=$true)][string] $Output,
    [string] $ItemConfigDir
)

$ErrorActionPreference = "Stop"
if (-not $Repo) { $Repo = $PWD.Path }
$patch = Join-Path $PSScriptRoot "patch_ofgui.py"
if (-not (Test-Path -LiteralPath $patch)) { throw "Patch script not found: $patch" }
if (-not $Project) { $Project = Join-Path $Repo "9963d_rxjh_fgui_project" }
if (-not $ItemConfigDir) { $ItemConfigDir = Join-Path $Repo "client\rjengineb_Data\StreamingAssets\Bundles\dev\Lua\game_config" }

Write-Host "==> patching ofgui"
python $patch $OfguiNodeModules
if ($LASTEXITCODE -ne 0) { throw "patch failed" }

$env:OFGUI_ITEM_PATH = Join-Path $ItemConfigDir "Item"
$env:OFGUI_ITEMEQUIP_PATH = Join-Path $ItemConfigDir "ItemEquip"
Write-Host "==> env: OFGUI_ITEM_PATH=$env:OFGUI_ITEM_PATH"

Write-Host "==> publishing: $Package"
$cli = Join-Path $OfguiNodeModules "@openfairygui\cli\bin\cli.cjs"
node $cli publish $Project -p $Package -o $Output
if ($LASTEXITCODE -ne 0) { throw "publish failed" }

Write-Host "==> done: $Output"
