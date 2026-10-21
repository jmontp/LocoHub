param(
    [Parameter(Mandatory=$true)][string]$OptionsPath,
    [Parameter(Mandatory=$true)][string]$CodeDirectory,
    [ValidateRange(512,2048)][int]$MemoryMiB = 2048,
    [ValidateRange(30,600)][int]$TimeoutSeconds = 300
)
$ErrorActionPreference = 'Stop'
$options = Get-Content -LiteralPath $OptionsPath -Raw | ConvertFrom-Json
$outputDir = Split-Path -Parent $options.output_path
if (-not $outputDir.StartsWith('S:\workspace\locomotion-data-standardization\converted_datasets\reconversion_v2\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Output must be in authorized S staging directory' }
if (Test-Path -LiteralPath $options.output_path) { throw 'Immutable output already exists' }
$free = [long](Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory * 1024
if ($free -lt (($MemoryMiB + 2048) * 1MB)) { throw 'Windows needs the hard limit plus 2 GiB available before launch' }
if ((Get-Volume -DriveLetter S).SizeRemaining -lt 5GB) { throw 'S free space below 5 GiB' }
New-Item -ItemType Directory -Force -Path "$outputDir\temp", "$outputDir\preferences" | Out-Null
$env:TEMP = "$outputDir\temp"; $env:TMP = $env:TEMP
$env:MATLAB_PREFDIR = "$outputDir\preferences"
$env:OMP_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'
# Create the child suspended, assign a kernel-enforced job memory limit, then
# resume it. Descendants remain in the job; closing it terminates only this job.
Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class MatlabJob {
 [StructLayout(LayoutKind.Sequential)] struct BasicLimit { public long ProcessTime, JobTime; public uint Flags; public UIntPtr MinWorking, MaxWorking; public uint Active; public UIntPtr Affinity; public uint Priority, Scheduling; }
 [StructLayout(LayoutKind.Sequential)] struct Io { public ulong A,B,C,D,E,F; }
 [StructLayout(LayoutKind.Sequential)] struct ExtendedLimit { public BasicLimit Basic; public Io Counters; public UIntPtr ProcessMemory, JobMemory, PeakProcess, PeakJob; }
 [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] struct Startup { public int cb; public string Reserved, Desktop, Title; public uint X,Y,XSize,YSize,XCount,YCount,Fill,Flags; public ushort Show,Reserved2; public IntPtr ReservedPtr,Input,Output,Error; }
 [StructLayout(LayoutKind.Sequential)] struct ProcessInfo { public IntPtr Process,Thread; public uint Id,ThreadId; }
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr CreateJobObject(IntPtr attrs,string name);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool SetInformationJobObject(IntPtr job,int cls,ref ExtendedLimit info,uint length);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool CreateProcess(string app,StringBuilder cmd,IntPtr pa,IntPtr ta,bool inherit,uint flags,IntPtr env,string cwd,ref Startup startup,out ProcessInfo pi);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr job,IntPtr process);
 [DllImport("kernel32.dll",SetLastError=true)] static extern uint ResumeThread(IntPtr thread);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetExitCodeProcess(IntPtr process,out uint exit);
 [DllImport("kernel32.dll")] static extern bool TerminateProcess(IntPtr process,uint code);
 [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
 public static IntPtr Job, Process;
 public static uint Id;
 public static void Start(string app,string args,string cwd,ulong bytes) {
  Job=CreateJobObject(IntPtr.Zero,null);
  if(Job==IntPtr.Zero) throw new System.ComponentModel.Win32Exception();
  var limits=new ExtendedLimit(); limits.Basic.Flags=0x2000|0x200|0x20;
  limits.Basic.Priority=0x40; limits.JobMemory=new UIntPtr(bytes);
  if(!SetInformationJobObject(Job,9,ref limits,(uint)Marshal.SizeOf(limits))) { Close(); throw new System.ComponentModel.Win32Exception(); }
  var startup=new Startup(); startup.cb=Marshal.SizeOf(startup); ProcessInfo pi;
  if(!CreateProcess(app,new StringBuilder("\""+app+"\" "+args),IntPtr.Zero,IntPtr.Zero,false,4,IntPtr.Zero,cwd,ref startup,out pi)) { Close(); throw new System.ComponentModel.Win32Exception(); }
  Process=pi.Process; Id=pi.Id;
  if(!AssignProcessToJobObject(Job,Process)) { TerminateProcess(Process,1); CloseHandle(pi.Thread); Close(); throw new System.ComponentModel.Win32Exception(); }
  if(ResumeThread(pi.Thread)==0xffffffff) { CloseHandle(pi.Thread); Close(); throw new System.ComponentModel.Win32Exception(); }
  CloseHandle(pi.Thread);
 }
 public static uint Status() { uint code; if(!GetExitCodeProcess(Process,out code)) throw new System.ComponentModel.Win32Exception(); return code; }
 public static void Close() { if(Job!=IntPtr.Zero) { CloseHandle(Job); Job=IntPtr.Zero; } if(Process!=IntPtr.Zero) { CloseHandle(Process); Process=IntPtr.Zero; } }
}
'@
$matlab = 'C:\Program Files\MATLAB\R2023b\bin\matlab.exe'
$escapedOptions = $OptionsPath.Replace("'", "''")
$expression = "options=jsondecode(fileread('$escapedOptions')); convert_gtech_2021_phase_to_parquet(options)"
$arguments = '-wait -singleCompThread -noFigureWindows -logfile "' + $outputDir + '\matlab.log" -batch "' + $expression + '"'
$state = @{ memory_limit_mib=$MemoryMiB; timeout_seconds=$TimeoutSeconds; status='starting'; started_utc=[DateTime]::UtcNow.ToString('o'); options=$OptionsPath }
$statusPath = Join-Path $outputDir 'native_status.json'
try {
 [MatlabJob]::Start($matlab,$arguments,$CodeDirectory,[UInt64]($MemoryMiB*1MB))
 $state.pid=[MatlabJob]::Id; $state.status='running'; $state | ConvertTo-Json | Set-Content -LiteralPath $statusPath
 $watch=[Diagnostics.Stopwatch]::StartNew()
 while ([MatlabJob]::Status() -eq 259) {
  if ($watch.Elapsed.TotalSeconds -gt $TimeoutSeconds) { throw 'MATLAB recording timeout' }
  if (([long](Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory*1024) -lt 1536MB) { throw 'Windows available memory fell below 1.5 GiB' }
  if ((Get-Volume -DriveLetter S).SizeRemaining -lt 5GB) { throw 'S free space fell below 5 GiB' }
  Start-Sleep -Milliseconds 500
 }
 $state.exit_code=[MatlabJob]::Status()
 if ($state.exit_code -ne 0) { throw "MATLAB exited with code $($state.exit_code)" }
 $state.status='completed'
} catch {
 $state.status='failed'; $state.reason=$_.Exception.Message
 throw
} finally {
 [MatlabJob]::Close()
 $state.finished_utc=[DateTime]::UtcNow.ToString('o')
 $state | ConvertTo-Json | Set-Content -LiteralPath $statusPath
}
