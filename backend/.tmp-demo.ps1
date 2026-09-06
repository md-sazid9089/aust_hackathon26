$ErrorActionPreference = 'Stop'
$B = 'http://localhost:8000/api/v1'
$H = @{ 'X-Dev-User' = 'faculty.dev@example.edu' }

$seed = Invoke-RestMethod -Method Post "$B/demo/seed" -Headers $H
"seed: course=$($seed.course_id) created=$($seed.created)"
$cid = $seed.course_id

$arts = Invoke-RestMethod "$B/courses/$cid/artefacts" -Headers $H
$arts | Select-Object id, kind, status, title | Format-Table -AutoSize | Out-String | Write-Host

$draft = ($arts | Where-Object { $_.title -match 'draft' -or $_.role -eq 'draft' } | Select-Object -First 1)
if (-not $draft) { $draft = $arts[-1] }
$past = @($arts | Where-Object { $_.id -ne $draft.id } | ForEach-Object { $_.id })
"draft=$($draft.id) past=$($past -join ',')"

$body = @{ module = 'exam_audit'; inputs = @{ draft_artefact_id = $draft.id; past_artefact_ids = $past } } | ConvertTo-Json -Depth 5
$run = Invoke-RestMethod -Method Post "$B/courses/$cid/runs" -Headers $H -ContentType 'application/json' -Body $body
"run=$($run.id) status=$($run.status)"

$deadline = (Get-Date).AddMinutes(4)
do {
    Start-Sleep -Seconds 4
    $run = Invoke-RestMethod "$B/runs/$($run.id)" -Headers $H
    "  $(Get-Date -Format HH:mm:ss) status=$($run.status) progress=$($run.progress)"
} while ($run.status -in @('queued', 'running') -and (Get-Date) -lt $deadline)

"FINAL status=$($run.status) error=$($run.error)"
$run.summary | ConvertTo-Json -Depth 5 -Compress

$f = Invoke-RestMethod "$B/runs/$($run.id)/findings" -Headers $H
"findings: $($f.Count)"
$f | Select-Object severity, rule_id, title | Format-Table -AutoSize | Out-String | Write-Host
