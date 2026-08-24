param(
    [Parameter(Mandatory = $true)][ValidateSet("generate", "edit")][string]$Mode,
    [Parameter(Mandatory = $true)][string]$Scene,
    [Parameter(Mandatory = $true)][string]$Output,
    [Parameter(Mandatory = $true)][string]$SceneHash,
    [string]$InputVsdx,
    [string]$Edits,
    [string]$BaseSceneHash,
    [string]$Preview
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Set-CellFormula {
    param([object]$Shape, [string]$CellName, [string]$Formula)
    $Shape.CellsU($CellName).FormulaU = $Formula
}

function Convert-ToVisioStringFormula {
    param([AllowEmptyString()][string]$Value)
    return '"' + $Value.Replace('"', '""') + '"'
}

function Convert-HexToRgbFormula {
    param([string]$Hex)
    $value = $Hex.TrimStart('#')
    if ($value.Length -ne 6) { throw "Expected #RRGGBB, received $Hex" }
    $red = [Convert]::ToInt32($value.Substring(0, 2), 16)
    $green = [Convert]::ToInt32($value.Substring(2, 2), 16)
    $blue = [Convert]::ToInt32($value.Substring(4, 2), 16)
    return "RGB($red,$green,$blue)"
}

function Add-ShapeData {
    param([object]$Shape, [string]$RowName, [string]$Label, [string]$Value)
    if (-not $Shape.CellExistsU("Prop.$RowName.Value", 0)) {
        [void]$Shape.AddNamedRow(243, $RowName, 0)
    }
    Set-CellFormula $Shape "Prop.$RowName.Label" (Convert-ToVisioStringFormula $Label)
    Set-CellFormula $Shape "Prop.$RowName.Value" (Convert-ToVisioStringFormula $Value)
}

function Add-MetadataRows {
    param([object]$Shape, [object]$Metadata)
    if ($null -eq $Metadata) { return }
    foreach ($property in $Metadata.PSObject.Properties) {
        Add-ShapeData $Shape ([string]$property.Name) ([string]$property.Name) ([string]$property.Value)
    }
}

function Get-ShapeDataValue {
    param([object]$Shape, [string]$RowName)
    if (-not $Shape.CellExistsU("Prop.$RowName.Value", 0)) { return $null }
    $formula = [string]$Shape.CellsU("Prop.$RowName.Value").FormulaU
    if ($formula.StartsWith('"') -and $formula.EndsWith('"')) {
        return $formula.Substring(1, $formula.Length - 2).Replace('""', '"')
    }
    return $formula
}

function Add-Ports {
    param([object]$Shape, [object[]]$Ports)
    foreach ($port in $Ports) {
        [void]$Shape.AddNamedRow(7, [string]$port.name, 0)
        Set-CellFormula $Shape "Connections.$($port.name).X" "Width*$([double]$port.x)"
        Set-CellFormula $Shape "Connections.$($port.name).Y" "Height*$([double]$port.y)"
        Set-CellFormula $Shape "Connections.$($port.name).DirX" ([string]$port.direction_x)
        Set-CellFormula $Shape "Connections.$($port.name).DirY" ([string]$port.direction_y)
        Set-CellFormula $Shape "Connections.$($port.name).Type" "0"
    }
}

function Get-ColorFormula {
    param([object]$SceneObject, [string]$Role)
    $color = [string]$SceneObject.theme.colors.$Role
    if (-not $color) { throw "Unknown semantic color role: $Role" }
    return Convert-HexToRgbFormula $color
}

function Set-ShapeStyle {
    param([object]$Shape, [object]$Item, [object]$SceneObject, [double]$ScaleX)
    $isText = [string]$Item.kind -eq "text"
    if ($isText) {
        Set-CellFormula $Shape "FillPattern" "0"
        Set-CellFormula $Shape "LinePattern" "0"
    } else {
        Set-CellFormula $Shape "FillForegnd" (Get-ColorFormula $SceneObject ([string]$Item.style.fill_role))
        Set-CellFormula $Shape "FillPattern" "1"
        $transparency = (1.0 - [double]$Item.style.fill_opacity) * 100.0
        Set-CellFormula $Shape "FillForegndTrans" "$transparency%"
        Set-CellFormula $Shape "LineColor" (Get-ColorFormula $SceneObject ([string]$Item.style.stroke_role))
        Set-CellFormula $Shape "LineWeight" "$([double]$Item.style.line_width_pt) pt"
        $pattern = switch ([string]$Item.style.line_pattern) {
            "solid" { 1 }
            "dashed" { 2 }
            "dotted" { 3 }
        }
        Set-CellFormula $Shape "LinePattern" ([string]$pattern)
        if ([double]$Item.style.line_width_pt -eq 0) {
            Set-CellFormula $Shape "LinePattern" "0"
        }
        if ([string]$Item.kind -eq "rounded_rectangle") {
            Set-CellFormula $Shape "Rounding" "$([double]$Item.style.radius * $ScaleX) in"
        }
    }
    Set-CellFormula $Shape "Char.Font" "FONT(`"$($SceneObject.theme.font_family)`")"
    Set-CellFormula $Shape "Char.Size" "$([double]$Item.style.font_size_pt) pt"
    Set-CellFormula $Shape "Char.Color" (Get-ColorFormula $SceneObject ([string]$Item.style.text_role))
    $align = switch ([string]$Item.style.align) {
        "left" { 0 }
        "center" { 1 }
        "right" { 2 }
    }
    Set-CellFormula $Shape "Para.HorzAlign" ([string]$align)
    Set-CellFormula $Shape "VerticalAlign" "1"
    Set-CellFormula $Shape "LeftMargin" "0.025 in"
    Set-CellFormula $Shape "RightMargin" "0.025 in"
    Set-CellFormula $Shape "TopMargin" "0.01 in"
    Set-CellFormula $Shape "BottomMargin" "0.01 in"
    $characters = $Shape.Characters
    $characters.Begin = 0
    $characters.End = [int]$characters.CharCount
    $characters.CharProps(2) = $(if ([int]$Item.style.font_weight -ge 600) { 1 } else { 0 })
}

function Set-ConnectorStyle {
    param([object]$Shape, [object]$Item, [object]$SceneObject)
    Set-CellFormula $Shape "LineColor" (Get-ColorFormula $SceneObject ([string]$Item.style.stroke_role))
    Set-CellFormula $Shape "LineWeight" "$([double]$Item.style.line_width_pt) pt"
    $pattern = switch ([string]$Item.style.line_pattern) {
        "solid" { 1 }
        "dashed" { 2 }
        "dotted" { 3 }
    }
    Set-CellFormula $Shape "LinePattern" ([string]$pattern)
    $arrow = switch ([string]$Item.style.arrowhead) {
        "none" { 0 }
        "standard" { 13 }
        "open" { 10 }
    }
    Set-CellFormula $Shape "EndArrow" ([string]$arrow)
}

function Set-ShapeGeometry {
    param([object]$Shape, [object]$Item, [double]$ScaleX, [double]$ScaleY)
    Set-CellFormula $Shape "PinX" "$(([double]$Item.x + [double]$Item.width / 2) * $ScaleX) in"
    Set-CellFormula $Shape "PinY" "$(([double]$Item.y + [double]$Item.height / 2) * $ScaleY) in"
    Set-CellFormula $Shape "Width" "$([double]$Item.width * $ScaleX) in"
    Set-CellFormula $Shape "Height" "$([double]$Item.height * $ScaleY) in"
}

if (-not (Test-Path -LiteralPath $Scene -PathType Leaf)) { throw "Scene does not exist: $Scene" }
if (Test-Path -LiteralPath $Output) { throw "Refusing to overwrite existing output: $Output" }
if ($Mode -eq "edit") {
    if (-not $InputVsdx -or -not (Test-Path -LiteralPath $InputVsdx -PathType Leaf)) {
        throw "Edit mode requires an existing -InputVsdx"
    }
    if (-not $Edits -or -not (Test-Path -LiteralPath $Edits -PathType Leaf)) {
        throw "Edit mode requires an existing -Edits request"
    }
    if (-not $BaseSceneHash) { throw "Edit mode requires -BaseSceneHash" }
}

$sceneObject = Get-Content -LiteralPath $Scene -Raw | ConvertFrom-Json
$scaleX = [double]$sceneObject.page.width_in / [double]$sceneObject.page.coordinate_width
$scaleY = [double]$sceneObject.page.height_in / [double]$sceneObject.page.coordinate_height
$outputParent = Split-Path -Parent $Output
if ($outputParent) { [void](New-Item -ItemType Directory -Force -Path $outputParent) }
if ($Preview) {
    $previewParent = Split-Path -Parent $Preview
    if ($previewParent) { [void](New-Item -ItemType Directory -Force -Path $previewParent) }
    if (Test-Path -LiteralPath $Preview) { throw "Refusing to overwrite preview: $Preview" }
}

$beforePids = @(Get-Process -Name VISIO -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
$result = [ordered]@{
    bridge_version = "1.0"
    mode = $Mode
    scene_id = [string]$sceneObject.scene_id
    scene_hash = $SceneHash
    output = [IO.Path]::GetFullPath($Output)
    process = [ordered]@{ before = $beforePids; owned = @(); after_quit = @() }
    page = [ordered]@{}
    close = [ordered]@{ quit_called = $false; owned_processes_closed = $false }
}

$app = $null
$doc = $null
$page = $null
$failure = $null
try {
    $app = New-Object -ComObject Visio.InvisibleApp
    $app.AlertResponse = 7
    Start-Sleep -Milliseconds 700
    $afterCreate = @(Get-Process -Name VISIO -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
    $result.process.after_create = $afterCreate
    $result.process.owned = @($afterCreate | Where-Object { $beforePids -notcontains $_ })
    if ($result.process.owned.Count -ne 1) {
        throw "Expected one separately owned Visio process, observed $($result.process.owned.Count)"
    }
    $result.visio = [ordered]@{
        product = [string]$app.ProductName
        version = [string]$app.Version
        build = [string]$app.Build
    }

    if ($Mode -eq "generate") {
        $doc = $app.Documents.Add("")
        $page = $doc.Pages.Item(1)
        $page.NameU = [string]$sceneObject.page.name
        $page.PageSheet.CellsU("PageWidth").FormulaU = "$($sceneObject.page.width_in) in"
        $page.PageSheet.CellsU("PageHeight").FormulaU = "$($sceneObject.page.height_in) in"
        foreach ($margin in @("PageLeftMargin", "PageRightMargin", "PageTopMargin", "PageBottomMargin")) {
            $page.PageSheet.CellsU($margin).FormulaU = "0 in"
        }
        Add-ShapeData $page.PageSheet "SceneID" "Scene ID" ([string]$sceneObject.scene_id)
        Add-ShapeData $page.PageSheet "SceneSchema" "Scene schema" ([string]$sceneObject.schema_version)
        Add-ShapeData $page.PageSheet "SceneHash" "Scene SHA-256" $SceneHash
        Add-MetadataRows $page.PageSheet $sceneObject.metadata
        $shapes = @{}
        foreach ($item in $sceneObject.shapes) {
            $x1 = [double]$item.x * $scaleX
            $y1 = [double]$item.y * $scaleY
            $x2 = ([double]$item.x + [double]$item.width) * $scaleX
            $y2 = ([double]$item.y + [double]$item.height) * $scaleY
            if ([string]$item.kind -eq "ellipse") {
                $shape = $page.DrawOval($x1, $y2, $x2, $y1)
            } else {
                $shape = $page.DrawRectangle($x1, $y2, $x2, $y1)
            }
            $shape.NameU = [string]$item.id
            $shape.Text = [string]$item.text
            Set-ShapeStyle $shape $item $sceneObject $scaleX
            Add-ShapeData $shape "SemanticID" "Semantic ID" ([string]$item.id)
            Add-ShapeData $shape "Role" "Semantic role" ([string]$item.role)
            if ($null -ne $item.parent) {
                Add-ShapeData $shape "ParentSemanticID" "Parent semantic ID" ([string]$item.parent)
            }
            Add-MetadataRows $shape $item.data
            Add-Ports $shape @($item.ports)
            $shapes[[string]$item.id] = $shape
        }
        $connectors = @{}
        foreach ($item in $sceneObject.connectors) {
            $source = $shapes[[string]$item.source.shape_id]
            $target = $shapes[[string]$item.target.shape_id]
            if (@($item.route).Count -ge 2) {
                [double[]]$coordinates = @()
                foreach ($point in $item.route) {
                    $coordinates += [double]$point.x * $scaleX
                    $coordinates += [double]$point.y * $scaleY
                }
                $connector = $page.DrawPolyline($coordinates, 8)
            } else {
                $connector = $page.Drop($app.ConnectorToolDataObject, 0.0, 0.0)
                Set-CellFormula $connector "ConLineRouteExt" "1"
                Set-CellFormula $connector "ShapeRouteStyle" "2"
            }
            $connector.NameU = [string]$item.id
            Set-ConnectorStyle $connector $item $sceneObject
            $connector.CellsU("BeginX").GlueTo(
                $source.CellsU("Connections.$($item.source.port).X")
            )
            $connector.CellsU("EndX").GlueTo(
                $target.CellsU("Connections.$($item.target.port).X")
            )
            Add-ShapeData $connector "SemanticID" "Semantic ID" ([string]$item.id)
            Add-ShapeData $connector "Role" "Semantic role" ([string]$item.role)
            Add-ShapeData $connector "Source" "Source semantic ID" ([string]$item.source.shape_id)
            Add-ShapeData $connector "Target" "Target semantic ID" ([string]$item.target.shape_id)
            $connectors[[string]$item.id] = $connector
        }
        foreach ($connector in $connectors.Values) { [void]$connector.SendToBack() }
        foreach ($shape in $shapes.Values) {
            if ((Get-ShapeDataValue $shape "Role") -eq "canvas") {
                [void]$shape.SendToBack()
            }
        }
        [void]$doc.SaveAs([IO.Path]::GetFullPath($Output))
    } else {
        $doc = $app.Documents.Open([IO.Path]::GetFullPath($InputVsdx))
        $page = $doc.Pages.Item(1)
        $storedHash = Get-ShapeDataValue $page.PageSheet "SceneHash"
        if ($storedHash -ne $BaseSceneHash) {
            throw "Stale VSDX scene hash: expected $BaseSceneHash, found $storedHash"
        }
        $bySemantic = @{}
        for ($index = 1; $index -le $page.Shapes.Count; $index++) {
            $shape = $page.Shapes.Item($index)
            $semanticId = Get-ShapeDataValue $shape "SemanticID"
            if (-not $semanticId) { continue }
            if ($bySemantic.ContainsKey($semanticId)) {
                throw "Ambiguous VSDX semantic ID: $semanticId"
            }
            $bySemantic[$semanticId] = $shape
        }
        $sceneElements = @{}
        foreach ($item in $sceneObject.shapes) { $sceneElements[[string]$item.id] = $item }
        foreach ($item in $sceneObject.connectors) { $sceneElements[[string]$item.id] = $item }
        $request = Get-Content -LiteralPath $Edits -Raw | ConvertFrom-Json
        if ([string]$request.scene_id -ne [string]$sceneObject.scene_id) {
            throw "Edit request scene_id does not match the revised scene"
        }
        if ([string]$request.base_scene_sha256 -ne $BaseSceneHash) {
            throw "Edit request base hash does not match -BaseSceneHash"
        }
        $editedIds = @()
        foreach ($operation in $request.edits) {
            $targetId = [string]$operation.target_id
            if ($editedIds -contains $targetId) { throw "Ambiguous repeated edit target: $targetId" }
            if (-not $bySemantic.ContainsKey($targetId)) { throw "Missing VSDX semantic ID: $targetId" }
            if (-not $sceneElements.ContainsKey($targetId)) { throw "Missing revised-scene ID: $targetId" }
            $shape = $bySemantic[$targetId]
            $item = $sceneElements[$targetId]
            if ($item.PSObject.Properties.Name -contains "source") {
                Set-ConnectorStyle $shape $item $sceneObject
            } else {
                Set-ShapeGeometry $shape $item $scaleX $scaleY
                $shape.Text = [string]$item.text
                Set-ShapeStyle $shape $item $sceneObject $scaleX
            }
            $editedIds += $targetId
        }
        Add-ShapeData $page.PageSheet "SceneHash" "Scene SHA-256" $SceneHash
        [void]$doc.SaveAs([IO.Path]::GetFullPath($Output))
        $result.edited_ids = $editedIds
    }

    if ($Preview) { [void]$page.Export([IO.Path]::GetFullPath($Preview)) }
    $result.page.shape_count = [int]$page.Shapes.Count
    $result.page.connect_count = [int]$page.Connects.Count
    $result.page.scene_hash = Get-ShapeDataValue $page.PageSheet "SceneHash"
    $doc.Close()
    $doc = $null
} catch {
    $failure = $_
} finally {
    if ($null -ne $doc) {
        try { $doc.Close() } catch { $result.close.document_close_error = $_.Exception.Message }
    }
    if ($null -ne $app) {
        try {
            $app.Quit()
            $result.close.quit_called = $true
        } catch {
            $result.close.quit_error = $_.Exception.Message
        }
    }
    $page = $null
    $doc = $null
    $app = $null
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
    Start-Sleep -Seconds 2
    $afterQuit = @(Get-Process -Name VISIO -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
    $result.process.after_quit = $afterQuit
    $remainingOwned = @($result.process.owned | Where-Object { $afterQuit -contains $_ })
    $result.process.remaining_owned = $remainingOwned
    $result.close.owned_processes_closed = $remainingOwned.Count -eq 0
}

if ($null -ne $failure) { throw $failure }
if (-not $result.close.owned_processes_closed) {
    throw "Task-owned Visio instance did not close normally; no process was terminated."
}
$result | ConvertTo-Json -Depth 8 -Compress
