param(
    [Parameter(Mandatory=$true)][string]$OptionsPath,
    [Parameter(Mandatory=$true)][string]$CodeDirectory,
    [ValidateRange(512,2048)][int]$MemoryMiB = 2048,
    [ValidateRange(30,600)][int]$TimeoutSeconds = 300,
    [ValidateSet('time','phase','prepare-transforms')][string]$Mode = 'time'
)
# Reuse the reviewed native job/memory/disk/timeout guard without modifying the
# frozen GT21 launcher used by the pending batch. Only the fixed entry point differs.
$ErrorActionPreference = 'Stop'
$guard = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'run_matlab_recording_guarded.ps1') -Raw
$old = 'convert_gtech_2021_phase_to_parquet(options)'
if (($guard.Split(@($old), [StringSplitOptions]::None).Length - 1) -ne 1) {
    throw 'Native guard entry point changed; review the GT23 adapter before running'
}
$entry = switch ($Mode) {
    'phase' { 'convert_gtech_phase_to_parquet(options)' }
    'prepare-transforms' { 'prepare_gt23_transforms(options)' }
    default { 'convert_gtech_2023_time_to_parquet(options)' }
}
$guard = $guard.Replace($old, $entry)
& ([ScriptBlock]::Create($guard)) -OptionsPath $OptionsPath -CodeDirectory $CodeDirectory -MemoryMiB $MemoryMiB -TimeoutSeconds $TimeoutSeconds
