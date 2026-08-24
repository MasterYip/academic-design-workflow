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

function Get-ActiveProcessIds([string]$Name) {
    return @(Get-Process $Name -ErrorAction SilentlyContinue | Where-Object { $_.Threads.Count -gt 0 } | Select-Object -ExpandProperty Id | Sort-Object)
}

function Test-ProcessIdSetEqual($Left, $Right) {
    # Compare the already sorted ID inventories as stable strings. Unlike
    # Compare-Object, this remains well-defined when either set is empty.
    return ((@($Left) -join ',') -eq (@($Right) -join ','))
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

$beforeVisio = Get-ActiveProcessIds 'VISIO'
$beforeWord = Get-ActiveProcessIds 'WINWORD'
$result = [ordered]@{ bridge_version='1.0'; input=$inputPath; output=$outputPath; replacements=@(); process=[ordered]@{before_visio=$beforeVisio;before_word=$beforeWord;owned_visio=@()} }
$app=$null; $doc=$null; $page=$null; $failure=$null
try {
    # Visio.Application exits cleanly after Word OLE rendering on supported
    # hosts; InvisibleApp can leave a zero-thread renderer entry behind.
    $app = New-Object -ComObject Visio.Application
    $app.Visible = $false
    $app.AlertResponse = 7
    Start-Sleep -Milliseconds 700
    $afterCreate = Get-ActiveProcessIds 'VISIO'
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
    $result.ole_object_count=[int]$page.OLEObjects.Count
    $ole=$null;$shape=$null;$placeholder=$null
    $doc.Close();$doc=$null;$page=$null
    # Reopen before preview export so Visio consumes the saved Word display
    # cache at the final geometry instead of exporting its stale insertion
    # position from the in-memory OLE session.
    if($Preview){
        $doc=$app.Documents.Open($outputPath)
        $page=$doc.Pages.Item(1)
        [void]$page.Export([IO.Path]::GetFullPath($Preview))
        $doc.Close();$doc=$null;$page=$null
    }
} catch { $failure=$_ }
finally {
    if($doc){try{$doc.Close()}catch{}}
    if($app){try{$app.Quit()}catch{}}
    $ole=$null;$shape=$null;$placeholder=$null;$page=$null;$doc=$null;$app=$null
    [GC]::Collect();[GC]::WaitForPendingFinalizers();[GC]::Collect();[GC]::WaitForPendingFinalizers()
    for($attempt=0;$attempt-lt 30;$attempt++){
        $current=Get-ActiveProcessIds 'VISIO'
        if(-not @($result.process.owned_visio|Where-Object{$_ -in $current})){break}
        Start-Sleep -Milliseconds 500
    }
    $afterVisio=Get-ActiveProcessIds 'VISIO'
    $afterWord=Get-ActiveProcessIds 'WINWORD'
    $result.process.after_visio=$afterVisio;$result.process.after_word=$afterWord
    $result.process.exited_owned_records=@(Get-Process VISIO -ErrorAction SilentlyContinue | Where-Object { $_.Id -in $result.process.owned_visio -and $_.Threads.Count -eq 0 } | ForEach-Object { [ordered]@{id=$_.Id;handle_count=$_.HandleCount;thread_count=$_.Threads.Count} })
    $result.process.preserved=(Test-ProcessIdSetEqual $beforeVisio $afterVisio) -and (Test-ProcessIdSetEqual $beforeWord $afterWord)
}
if($failure){throw $failure}
if(-not $result.process.preserved){throw "Office process set changed: Visio $($beforeVisio -join ',') -> $($result.process.after_visio -join ','); Word $($beforeWord -join ',') -> $($result.process.after_word -join ',')"}
$result|ConvertTo-Json -Depth 8 -Compress
