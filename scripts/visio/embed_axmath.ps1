param(
    [Parameter(Mandatory = $true)][string]$InputVsdx,
    [Parameter(Mandatory = $true)][string]$OutputVsdx,
    [Parameter(Mandatory = $true)][string]$Manifest,
    [Parameter(Mandatory = $true)][string]$Record,
    [string]$Preview
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Get-ProcessIds([string]$Name) {
    return @(Get-Process $Name -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id | Sort-Object)
}

function Test-IdSetEqual($Left, $Right) {
    return ((@($Left) -join ',') -eq (@($Right) -join ','))
}

function Release-ComObject($Value) {
    if ($null -ne $Value -and [Runtime.InteropServices.Marshal]::IsComObject($Value)) {
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($Value)
    }
}

function Quote-ShapeSheetString([string]$Value) {
    return '"' + $Value.Replace('"', '""') + '"'
}

function Set-StringShapeData($Shape, [string]$Name, [string]$Label, [string]$Value) {
    if ($Shape.SectionExists(243, 0) -eq 0) { [void]$Shape.AddSection(243) }
    if ($Shape.CellExistsU("Prop.$Name", 0) -eq 0) { [void]$Shape.AddNamedRow(243, $Name, 0) }
    $Shape.CellsU("Prop.$Name.Label").FormulaU = Quote-ShapeSheetString $Label
    $Shape.CellsU("Prop.$Name.Type").FormulaU = '0'
    $Shape.CellsU("Prop.$Name.Value").FormulaU = Quote-ShapeSheetString $Value
}

function Position-Equation($Shape, [double]$PinX, [double]$PinY, [double]$MaxWidth, [double]$MaxHeight) {
    $naturalWidth = [double]$Shape.CellsU('Width').ResultIU
    $naturalHeight = [double]$Shape.CellsU('Height').ResultIU
    if ($naturalWidth -le 0 -or $naturalHeight -le 0) {
        throw "Invalid natural AxMath dimensions for $($Shape.NameU): $naturalWidth x $naturalHeight"
    }
    $scale = [Math]::Min($MaxWidth / $naturalWidth, $MaxHeight / $naturalHeight)
    $Shape.CellsU('Width').ResultIU = $naturalWidth * $scale
    $Shape.CellsU('Height').ResultIU = $naturalHeight * $scale
    $Shape.CellsU('PinX').ResultIU = $PinX
    $Shape.CellsU('PinY').ResultIU = $PinY
}

$inputPath = [IO.Path]::GetFullPath($InputVsdx)
$outputPath = [IO.Path]::GetFullPath($OutputVsdx)
$manifestPath = [IO.Path]::GetFullPath($Manifest)
$recordPath = [IO.Path]::GetFullPath($Record)
$previewPath = if ($Preview) { [IO.Path]::GetFullPath($Preview) } else { $null }
foreach ($path in @($inputPath, $manifestPath)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing input: $path" }
}
foreach ($path in @($outputPath, $recordPath, $previewPath)) {
    if ($path -and (Test-Path -LiteralPath $path)) { throw "Refusing to overwrite output: $path" }
}

$config = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ([string]$config.schema_version -ne '1.0') { throw 'Unsupported AxMath manifest schema' }
$replacements = @($config.replacements)
if ($replacements.Count -lt 1) { throw 'AxMath manifest has no replacements' }
$equationIds = @($replacements | ForEach-Object {
    if ($_.PSObject.Properties.Name -contains 'equation_id') {
        [string]$_.equation_id
    } else {
        'axmath_' + [string]$_.target_id
    }
})
if (@($equationIds | Sort-Object -Unique).Count -ne $equationIds.Count) {
    throw 'AxMath equation IDs must be unique'
}
foreach ($item in $replacements) {
    if ([string]::IsNullOrWhiteSpace([string]$item.target_id)) { throw 'Every replacement needs target_id' }
    if ([string]::IsNullOrWhiteSpace([string]$item.latex)) { throw "Missing LaTeX for $($item.target_id)" }
    if ([double]$item.max_width -le 0 -or [double]$item.max_height -le 0) {
        throw "max_width and max_height must be positive for $($item.target_id)"
    }
}

foreach ($path in @($outputPath, $recordPath, $previewPath)) {
    if ($path) { [void](New-Item -ItemType Directory -Path (Split-Path $path) -Force) }
}
$recordStem = [IO.Path]::GetFileNameWithoutExtension($recordPath)
$assetDirectory = Join-Path (Split-Path $recordPath) ($recordStem + '.afx')
[void](New-Item -ItemType Directory -Path $assetDirectory -Force)
$builder = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'build_axmath_object.ps1'

$before = [ordered]@{
    visio = Get-ProcessIds 'VISIO'
    axmath = Get-ProcessIds 'AxMath'
    word = Get-ProcessIds 'WINWORD'
    powerpoint = Get-ProcessIds 'POWERPNT'
}
$assets = [Collections.ArrayList]::new()
$shapeRecords = [Collections.ArrayList]::new()
$assetByLatex = @{}
$connectorFixedCodes = [Collections.ArrayList]::new()
$app = $null
$doc = $null
$page = $null
$failure = $null
$ownedVisio = @()

try {
    foreach ($item in $replacements) {
        $latex = [string]$item.latex
        if (-not $assetByLatex.ContainsKey($latex)) {
            $assetPath = Join-Path $assetDirectory ('equation_{0:D3}.afx' -f ($assetByLatex.Count + 1))
            $stdoutPath = $assetPath + '.stdout.txt'
            & $builder -OutputAfx $assetPath -Latex $latex 2>&1 | Set-Content -LiteralPath $stdoutPath -Encoding utf8
            if ($LASTEXITCODE -ne 0) { throw "AxMath generation failed for $latex" }
            $assetByLatex[$latex] = $assetPath
            [void]$assets.Add([ordered]@{
                latex = $latex
                path = $assetPath
                sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $assetPath).Hash
                size_bytes = (Get-Item -LiteralPath $assetPath).Length
                stdout = $stdoutPath
            })
        }
    }

    Copy-Item -LiteralPath $inputPath -Destination $outputPath
    $app = New-Object -ComObject Visio.InvisibleApp
    $app.AlertResponse = 7
    Start-Sleep -Milliseconds 700
    $ownedVisio = @(Get-ProcessIds 'VISIO' | Where-Object { $_ -notin $before.visio })
    if ($ownedVisio.Count -ne 1) { throw "Expected one owned Visio PID; found $($ownedVisio -join ',')" }
    $doc = $app.Documents.Open($outputPath)
    $page = $doc.Pages.Item(1)

    $existingNames = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($existingShape in $page.Shapes) {
        try {
            [void]$existingNames.Add([string]$existingShape.NameU)
            if ([int]$existingShape.OneD -ne 0) {
                [void]$connectorFixedCodes.Add([ordered]@{
                    name = [string]$existingShape.NameU
                    formula = [string]$existingShape.CellsU('ConFixedCode').FormulaU
                })
                $existingShape.CellsU('ConFixedCode').FormulaU = '2'
            }
        } finally {
            Release-ComObject $existingShape
        }
    }

    foreach ($item in $replacements) {
        $carrier = $null
        $equation = $null
        $ole = $null
        try {
            $targetId = [string]$item.target_id
            $equationId = if ($item.PSObject.Properties.Name -contains 'equation_id') {
                [string]$item.equation_id
            } else {
                'axmath_' + $targetId
            }
            if ($existingNames.Contains($equationId)) { throw "Equation ID already exists: $equationId" }
            $carrier = $page.Shapes.ItemU($targetId)
            if ($item.PSObject.Properties.Name -contains 'carrier_text') {
                $carrier.Text = [string]$item.carrier_text
            }
            $sourceLatex = if ($item.PSObject.Properties.Name -contains 'source_latex') {
                [string]$item.source_latex
            } else {
                [string]$item.latex
            }
            Set-StringShapeData $carrier 'SourceText' 'Exact LaTeX source' ('$' + $sourceLatex + '$')

            $equation = $page.InsertFromFile([string]$assetByLatex[[string]$item.latex], 16384)
            $equation.NameU = $equationId
            $pinX = if ($item.PSObject.Properties.Name -contains 'pin_x') { [double]$item.pin_x } else { [double]$carrier.CellsU('PinX').ResultIU }
            $pinY = if ($item.PSObject.Properties.Name -contains 'pin_y') { [double]$item.pin_y } else { [double]$carrier.CellsU('PinY').ResultIU }
            Position-Equation $equation $pinX $pinY ([double]$item.max_width) ([double]$item.max_height)
            $equation.CellsU('LinePattern').FormulaU = '0'
            $equation.CellsU('FillPattern').FormulaU = '0'
            $equation.CellsU('ShapePermeableX').FormulaU = 'TRUE'
            $equation.CellsU('ShapePermeableY').FormulaU = 'TRUE'
            $equation.CellsU('ShapePlowCode').FormulaU = '1'
            $equation.CellsU('ShapeFixedCode').FormulaU = '4'
            Set-StringShapeData $equation 'SemanticID' 'Semantic ID' $equationId
            Set-StringShapeData $equation 'Role' 'Semantic role' 'equation'
            Set-StringShapeData $equation 'ParentSemanticID' 'Parent semantic ID' $targetId
            Set-StringShapeData $equation 'SourceText' 'Exact LaTeX source' ('$' + $sourceLatex + '$')
            Set-StringShapeData $equation 'DisplayLatex' 'AxMath display LaTeX' ('$' + [string]$item.latex + '$')
            Set-StringShapeData $equation 'AxMathProgID' 'OLE ProgID' 'Equation.AxMath'
            Set-StringShapeData $equation 'AxMathCLSID' 'OLE CLSID' '{B18C2BCC-4E79-436A-A2A5-A7F8D25A9A28}'
            $ole = $page.OLEObjects.Item($page.OLEObjects.Count)
            if ([string]$ole.ProgID -ne 'Equation.AxMath') {
                throw "Unexpected OLE ProgID for ${equationId}: $($ole.ProgID)"
            }
            [void]$shapeRecords.Add([ordered]@{
                target_id = $targetId
                equation_id = $equationId
                latex = [string]$item.latex
                source_latex = $sourceLatex
                prog_id = [string]$ole.ProgID
                class_id = [string]$ole.ClassID
                pin_x = [double]$equation.CellsU('PinX').ResultIU
                pin_y = [double]$equation.CellsU('PinY').ResultIU
                width = [double]$equation.CellsU('Width').ResultIU
                height = [double]$equation.CellsU('Height').ResultIU
            })
            [void]$existingNames.Add($equationId)
        } finally {
            Release-ComObject $ole
            Release-ComObject $equation
            Release-ComObject $carrier
        }
    }

    foreach ($connectorRecord in $connectorFixedCodes) {
        $connector = $null
        try {
            $connector = $page.Shapes.ItemU($connectorRecord.name)
            $connector.CellsU('ConFixedCode').FormulaU = $connectorRecord.formula
        } finally {
            Release-ComObject $connector
        }
    }
    [void]$doc.Save()
    if ($previewPath) {
        $doc.Close()
        Release-ComObject $page
        Release-ComObject $doc
        $page = $null
        $doc = $null
        $doc = $app.Documents.Open($outputPath)
        $page = $doc.Pages.Item(1)
        [void]$page.Export($previewPath)
    }
} catch {
    $failure = $_
} finally {
    if ($doc) { try { $doc.Close() } catch {} }
    Release-ComObject $page
    Release-ComObject $doc
    if ($app -and $ownedVisio.Count -eq 1) { try { $app.Quit() } catch {} }
    Release-ComObject $app
    $page = $null
    $doc = $null
    $app = $null
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        $ownedAlive = @(
            (Get-ProcessIds 'VISIO' | Where-Object { $_ -notin $before.visio }) +
            (Get-ProcessIds 'AxMath' | Where-Object { $_ -notin $before.axmath })
        )
        if ($ownedAlive.Count -eq 0) { break }
        Start-Sleep -Milliseconds 500
    }
}

$after = [ordered]@{
    visio = Get-ProcessIds 'VISIO'
    axmath = Get-ProcessIds 'AxMath'
    word = Get-ProcessIds 'WINWORD'
    powerpoint = Get-ProcessIds 'POWERPNT'
}
$result = [ordered]@{
    schema_version = '1.0'
    input = $inputPath
    input_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $inputPath).Hash
    output = $outputPath
    output_sha256 = if (Test-Path -LiteralPath $outputPath) { (Get-FileHash -Algorithm SHA256 -LiteralPath $outputPath).Hash } else { $null }
    manifest = $manifestPath
    prog_id = 'Equation.AxMath'
    clsid = '{B18C2BCC-4E79-436A-A2A5-A7F8D25A9A28}'
    assets = $assets
    replacements = $shapeRecords
    before = $before
    owned_visio = $ownedVisio
    after = $after
    process_sets_preserved =
        (Test-IdSetEqual $before.visio $after.visio) -and
        (Test-IdSetEqual $before.axmath $after.axmath) -and
        (Test-IdSetEqual $before.word $after.word) -and
        (Test-IdSetEqual $before.powerpoint $after.powerpoint)
    failure = if ($failure) { $failure.Exception.ToString() } else { $null }
}
$result | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $recordPath -Encoding utf8
if ($failure) { throw $failure }
if (-not $result.process_sets_preserved) { throw 'Office/AxMath process sets changed; no process was terminated.' }
$result | ConvertTo-Json -Depth 4 -Compress
