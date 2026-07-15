$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$VenvDir = Join-Path $ProjectDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $VenvPython)) {
    $Uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($Uv) {
        & $Uv.Source venv $VenvDir --python 3.10 --seed
    } else {
        $Py = Get-Command py -ErrorAction SilentlyContinue
        if (-not $Py) {
            throw "Install Python 3.10 or uv before running this script."
        }
        & $Py.Source -3.10 -m venv $VenvDir
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Virtual environment creation failed with exit code $LASTEXITCODE"
    }
}

& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }

& $VenvPython -m pip install "torch==2.10.0" --index-url https://download.pytorch.org/whl/cu128
if ($LASTEXITCODE -ne 0) { throw "CUDA-enabled PyTorch installation failed." }

& $VenvPython -m pip install -r (Join-Path $ProjectDir "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Runtime dependency installation failed." }

& $VenvPython -m pip install -r (Join-Path $ProjectDir "requirements-build.txt")
if ($LASTEXITCODE -ne 0) { throw "Build dependency installation failed." }

Write-Host "Environment ready: $VenvDir"
& $VenvPython -c "import torch; print('PyTorch:', torch.__version__); print('CUDA:', torch.version.cuda); print('CUDA available:', torch.cuda.is_available()); print('Architectures:', torch.cuda.get_arch_list())"
