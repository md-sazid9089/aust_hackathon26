$ErrorActionPreference = 'Continue'
$pw = (Select-String -Path e:\aust_hackathon26\backend\.env -Pattern '^SEED_FACULTY_PASSWORD=(.*)$').Matches[0].Groups[1].Value.Trim()
$base = 'http://localhost:5173/api/v1'
$tok = (Invoke-RestMethod -Method Post -Uri "$base/auth/login" -ContentType 'application/json' -Body (@{email = 'faculty@aust.edu'; password = $pw } | ConvertTo-Json)).access_token
$h = @{Authorization = "Bearer $tok" }
$me = Invoke-RestMethod -Uri "$base/me" -Headers $h
"me: $($me.email) role=$($me.role)"
$courses = Invoke-RestMethod -Uri "$base/courses" -Headers $h
$items = if ($courses.items) { $courses.items } else { $courses }
"courses: $($items.Count)"
foreach ($c in $items | Select-Object -First 3) {
    $arts = Invoke-RestMethod -Uri "$base/courses/$($c.id)/artefacts" -Headers $h
    $aitems = @($arts)
    "course $($c.code) id=$($c.id): $($aitems.Count) artefacts"
    foreach ($a in $aitems) { "  $($a.kind) '$($a.label)' status=$($a.status) id=$($a.id)" }
    try {
        $runs = Invoke-RestMethod -Uri "$base/courses/$($c.id)/runs" -Headers $h
        $ritems = if ($runs.items) { $runs.items } else { $runs }
        "  runs: $($ritems.Count) ; completed=$(@($ritems | Where-Object status -eq 'completed').Count)"
    }
    catch { "  runs: $($_.Exception.Response.StatusCode.value__)" }
}
if ($env:PROBE_DELETE_ID) {
    try { Invoke-RestMethod -Method Delete -Uri "$base/artefacts/$env:PROBE_DELETE_ID" -Headers $h | Out-Null; "DELETED" }
    catch { "FAIL -> $($_.Exception.Response.StatusCode.value__) $($_.ErrorDetails.Message)" }
}
