param(
    [Parameter(Mandatory = $true)][string]$InputVsdx,
    [Parameter(Mandatory = $true)][string]$OutputVsdx,
    [Parameter(Mandatory = $true)][string]$Manifest,
    [string]$Preview
)

$ErrorActionPreference = 'Stop'

function Quote-ShapeSheetString([string]$Value) {
    return '"' + $Value.Replace('"', '""') + '"'
}

function Add-ShapeData($Shape, [string]$Name, [string]$Label, [string]$Value) {
    if ($Shape.SectionExists(243, 0) -eq 0) { [void]$Shape.AddSection(243) }
    if ($Shape.CellExistsU("Prop.$Name", 0) -eq 0) { [void]$Shape.AddNamedRow(243, $Name, 0) }
    $Shape.CellsU("Prop.$Name.Label").FormulaU = Quote-ShapeSheetString $Label
    $Shape.CellsU("Prop.$Name.Value").FormulaU = Quote-ShapeSheetString $Value
}

$inputPath = [IO.Path]::GetFullPath($InputVsdx)
$outputPath = [IO.Path]::GetFullPath($OutputVsdx)
$manifestPath = [IO.Path]::GetFullPath($Manifest)
if (-not (Test-Path -LiteralPath $inputPath -PathType Leaf)) { throw "Missing input VSDX: $inputPath" }
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Missing Office Math manifest: $manifestPath" }
if (Test-Path -LiteralPath $outputPath) { throw "Refusing to overwrite output VSDX: $outputPath" }
if ($Preview -and (Test-Path -LiteralPath $Preview)) { throw "Refusing to overwrite preview: $Preview" }

$config = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ([string]$config.schema_version -ne '1.0') { throw 'Unsupported Office Math manifest schema' }
if (@($config.replacements).Count -lt 1) { throw 'Office Math manifest has no replacements' }

$beforeVisio = @(Get-Process VISIO -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id | Sort-Object)
$beforeWord = @(Get-Process WINWORD -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id | Sort-Object)
$result = [ordered]@{ bridge_version='1.0'; input=$inputPath; output=$outputPath; replacements=@(); process=[ordered]@{before_visio=$beforeVisio;before_word=$beforeWord;owned_visio=@()} }
$app=$null; $doc=$null; $page=$null; $failure=$null
try {
    $app = New-Object -ComObject Visio.InvisibleApp
    $app.AlertResponse = 7
    Start-Sleep -Milliseconds 700
    $afterCreate = @(Get-Process VISIO -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id | Sort-Object)
    $result.process.owned_visio = @($afterCreate | Where-Object { $_ -notin $beforeVisio })
    if ($result.process.owned_visio.Count -ne 1) { throw "Expected one owned Visio process, found $($result.process.owned_visio -join ',')" }
    $doc = $app.Documents.Open($inputPath)
    $page = $doc.Pages.Item(1)
    foreach($item in $config.replacements) {
        $targetId=[string]$item.target_id
        $docx=[IO.Path]::GetFullPath([string]$item.docx)
        if (-not (Test-Path -LiteralPath $docx -PathType Leaf)) { throw "Missing Office Math DOCX for ${targetId}: $docx" }
        $placeholder=$page.Shapes.ItemU($targetId)
        $geometry=[ordered]@{}
        foreach($cell in @('PinX','PinY','Width','Height','Angle')) { $geometry[$cell]=[double]$placeholder.CellsU($cell).ResultIU }
        $placeholder.Delete()
        $shape=$page.InsertFromFile($docx,0)
        $shape.NameU=$targetId
        foreach($cell in $geometry.Keys) { $shape.CellsU($cell).ResultIU=$geometry[$cell] }
        Add-ShapeData $shape 'SemanticID' 'Semantic ID' $targetId
        Add-ShapeData $shape 'Role' 'Semantic role' 'office_math'
        if ($item.parent) { Add-ShapeData $shape 'ParentSemanticID' 'Parent semantic ID' ([string]$item.parent) }
        foreach($property in $item.data.PSObject.Properties) { Add-ShapeData $shape ([string]$property.Name) ([string]$property.Name) ([string]$property.Value) }
        Add-ShapeData $shape 'OfficeMathProgID' 'Office Math ProgID' 'Word.Document.12'
        Add-ShapeData $shape 'OfficeMathEditable' 'Office Math editable' 'true'
        $ole=$page.OLEObjects.Item($page.OLEObjects.Count)
        if ([string]$ole.ProgID -ne 'Word.Document.12') { throw "Unexpected OLE ProgID for ${targetId}: $($ole.ProgID)" }
        $result.replacements += [ordered]@{target_id=$targetId;docx=$docx;progid=[string]$ole.ProgID;class_id=[string]$ole.ClassID;foreign_type=[int]$ole.ForeignType}
    }
    [void]$doc.SaveAs($outputPath)
    if($Preview){[void]$page.Export([IO.Path]::GetFullPath($Preview))}
    $result.ole_object_count=[int]$page.OLEObjects.Count
    $doc.Close();$doc=$null
} catch { $failure=$_ }
finally {
    if($doc){try{$doc.Close()}catch{}}
    if($app){try{$app.Quit()}catch{}}
    $page=$null;$doc=$null;$app=$null
    [GC]::Collect();[GC]::WaitForPendingFinalizers();[GC]::Collect();[GC]::WaitForPendingFinalizers()
    for($attempt=0;$attempt-lt 30;$attempt++){
        $current=@(Get-Process VISIO -ErrorAction SilentlyContinue|Select-Object -ExpandProperty Id|Sort-Object)
        if(-not @($result.process.owned_visio|Where-Object{$_ -in $current})){break}
        Start-Sleep -Milliseconds 500
    }
    $afterVisio=@(Get-Process VISIO -ErrorAction SilentlyContinue|Select-Object -ExpandProperty Id|Sort-Object)
    $afterWord=@(Get-Process WINWORD -ErrorAction SilentlyContinue|Select-Object -ExpandProperty Id|Sort-Object)
    $result.process.after_visio=$afterVisio;$result.process.after_word=$afterWord
    $result.process.preserved=(Compare-Object $beforeVisio $afterVisio).Count -eq 0 -and (Compare-Object $beforeWord $afterWord).Count -eq 0
}
if($failure){throw $failure}
if(-not $result.process.preserved){throw "Office process set changed: Visio $($beforeVisio -join ',') -> $($result.process.after_visio -join ','); Word $($beforeWord -join ',') -> $($result.process.after_word -join ',')"}
$result|ConvertTo-Json -Depth 8 -Compress
