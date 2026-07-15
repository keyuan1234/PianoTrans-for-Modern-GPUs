param(
    [string]$FFmpegPath = ""
)

$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$Spec = Join-Path $ProjectDir "PianoTrans-for-Modern-GPUs.spec"
$Checkpoint = Join-Path $ProjectDir "assets\piano_transcription_inference_data\note_F1=0.9677_pedal_F1=0.9186.pth"
$DistRoot = Join-Path $ProjectDir "dist"
$DistDir = Join-Path $DistRoot "PianoTrans-for-Modern-GPUs-Portable"
$BuildDir = Join-Path $ProjectDir "build"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Environment not found. Run scripts\setup_environment.ps1 first."
}

if (-not (Test-Path -LiteralPath $Checkpoint)) {
    & (Join-Path $ProjectDir "scripts\download_checkpoint.ps1")
    if ($LASTEXITCODE -ne 0) { throw "Checkpoint download failed." }
}

if (-not $FFmpegPath) {
    $BundledFFmpeg = Join-Path $ProjectDir "assets\ffmpeg\ffmpeg.exe"
    if (Test-Path -LiteralPath $BundledFFmpeg) {
        $FFmpegPath = $BundledFFmpeg
    } else {
        $FFmpegCommand = Get-Command ffmpeg -ErrorAction SilentlyContinue
        if ($FFmpegCommand) {
            $FFmpegPath = $FFmpegCommand.Source
        }
    }
}

if (-not $FFmpegPath -or -not (Test-Path -LiteralPath $FFmpegPath)) {
    throw "FFmpeg was not found. Place ffmpeg.exe in assets\ffmpeg or pass -FFmpegPath."
}

$ResolvedRoot = [IO.Path]::GetFullPath($ProjectDir).TrimEnd('\') + '\'
$ResolvedDist = [IO.Path]::GetFullPath($DistDir)
if (-not $ResolvedDist.StartsWith($ResolvedRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove a build path outside the repository: $ResolvedDist"
}
if (Test-Path -LiteralPath $DistDir) {
    Remove-Item -LiteralPath $DistDir -Recurse -Force
}

$env:PIANOTRANS_CHECKPOINT = [IO.Path]::GetFullPath($Checkpoint)
$env:PIANOTRANS_FFMPEG = [IO.Path]::GetFullPath($FFmpegPath)

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --distpath $DistRoot `
    --workpath $BuildDir `
    $Spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

Copy-Item -LiteralPath (Join-Path $ProjectDir "README.md") -Destination $DistDir -Force

$Exe = Join-Path $DistDir "PianoTrans-for-Modern-GPUs.exe"
if (-not (Test-Path -LiteralPath $Exe)) {
    throw "Build completed without the expected executable: $Exe"
}

$Size = (Get-ChildItem -LiteralPath $DistDir -Recurse -File | Measure-Object Length -Sum).Sum
Write-Host "Portable build completed."
Write-Host "Executable: $Exe"
Write-Host ("Folder size: {0:N2} GiB" -f ($Size / 1GB))
