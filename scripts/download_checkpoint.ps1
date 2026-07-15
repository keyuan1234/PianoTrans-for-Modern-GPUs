$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$TargetDir = Join-Path $ProjectDir "assets\piano_transcription_inference_data"
$Target = Join-Path $TargetDir "note_F1=0.9677_pedal_F1=0.9186.pth"
$Uri = "https://zenodo.org/record/4034264/files/CRNN_note_F1%3D0.9677_pedal_F1%3D0.9186.pth?download=1"

New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null

if ((Test-Path -LiteralPath $Target) -and (Get-Item -LiteralPath $Target).Length -gt 160MB) {
    Write-Host "Checkpoint already present: $Target"
    exit 0
}

Write-Host "Downloading the ByteDance piano transcription checkpoint..."
Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $Target

if ((Get-Item -LiteralPath $Target).Length -le 160MB) {
    Remove-Item -LiteralPath $Target -Force
    throw "Checkpoint download was incomplete. Run this script again."
}

Write-Host "Checkpoint downloaded: $Target"
