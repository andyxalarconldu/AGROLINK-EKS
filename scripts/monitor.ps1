$URL = "http://a34d5348244ad4d32b45239e0a9f4f31-244711681.us-east-1.elb.amazonaws.com/health"
$ok = 0; $err = 0
while ($true) {
  try { Invoke-RestMethod -Uri $URL -TimeoutSec 2 | Out-Null; $ok++ } catch { $err++ }
  Write-Host "$(Get-Date -Format HH:mm:ss) OK=$ok ERRORES=$err"
  Start-Sleep -Milliseconds 500
}