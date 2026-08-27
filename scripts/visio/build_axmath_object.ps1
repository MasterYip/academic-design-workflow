param(
    [Parameter(Mandatory = $true)][string]$OutputAfx,
    [Parameter(Mandatory = $true)][string]$Latex,
    [string]$HelperOutput
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Add-Type -AssemblyName System.Windows.Forms

$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$source = Join-Path $scriptDirectory 'AxMathOleDirect.cs'
$output = [IO.Path]::GetFullPath($OutputAfx)
if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Missing AxMath helper source: $source" }
if (Test-Path -LiteralPath $output) { throw "Refusing to overwrite output: $output" }
[void](New-Item -ItemType Directory -Path (Split-Path $output) -Force)

$helper = if ([string]::IsNullOrWhiteSpace($HelperOutput)) {
    Join-Path ([IO.Path]::GetTempPath()) 'academic-design-workflow-AxMathOleDirect.exe'
} else {
    [IO.Path]::GetFullPath($HelperOutput)
}
$csc = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $csc -PathType Leaf)) { throw "Missing 32-bit C# compiler: $csc" }

$axmathType = [Type]::GetTypeFromProgID('Equation.AxMath')
if ($null -eq $axmathType) { throw 'AxMath is not installed or Equation.AxMath is not registered' }
$expectedClsid = [Guid]'B18C2BCC-4E79-436A-A2A5-A7F8D25A9A28'
if ($axmathType.GUID -ne $expectedClsid) {
    throw "Unexpected Equation.AxMath CLSID: $($axmathType.GUID)"
}

if (-not (Test-Path -LiteralPath $helper -PathType Leaf) -or
    (Get-Item -LiteralPath $helper).LastWriteTimeUtc -lt (Get-Item -LiteralPath $source).LastWriteTimeUtc) {
    & $csc /nologo /target:exe /platform:x86 /reference:System.Windows.Forms.dll "/out:$helper" $source
    if ($LASTEXITCODE -ne 0) { throw "AxMath helper compilation failed with exit code $LASTEXITCODE" }
}

$savedClipboard = [Windows.Forms.Clipboard]::GetDataObject()
try {
    & $helper $output $Latex
    if ($LASTEXITCODE -ne 0) { throw "AxMath object generation failed with exit code $LASTEXITCODE" }
} finally {
    for ($attempt = 0; $attempt -lt 10; $attempt++) {
        try {
            [Windows.Forms.Clipboard]::SetDataObject($savedClipboard, $true)
            break
        } catch {
            if ($attempt -eq 9) { Write-Warning 'Unable to restore the clipboard after ten attempts' }
            Start-Sleep -Milliseconds 250
        }
    }
}

[ordered]@{
    schema_version = '1.0'
    output = $output
    sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $output).Hash
    size_bytes = (Get-Item -LiteralPath $output).Length
    latex = $Latex
    prog_id = 'Equation.AxMath'
    clsid = '{B18C2BCC-4E79-436A-A2A5-A7F8D25A9A28}'
    helper = $helper
} | ConvertTo-Json -Depth 4 -Compress
