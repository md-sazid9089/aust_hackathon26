# Local smoke test: login (AUTH_MODE=local) then exercise CRUD against the running backend.
$B = 'http://localhost:8000/api/v1'
$tok = (Invoke-RestMethod -Method Post -Uri "$B/auth/login" -ContentType 'application/json' -Body '{"email":"faculty@aust.edu","password":"Faculty#2026"}').access_token
$H = @{ Authorization = "Bearer $tok" }
Write-Host "me:" ((Invoke-RestMethod -Uri "$B/me" -Headers $H) | ConvertTo-Json -Compress)

$c = Invoke-RestMethod -Method Post -Uri "$B/courses" -Headers $H -ContentType 'application/json' -Body '{"code":"CSE 9999","title":"Smoke Test Course","term":"Fall 2026","level":"UG"}'
Write-Host "created course:" $c.id $c.code
$c2 = Invoke-RestMethod -Method Patch -Uri "$B/courses/$($c.id)" -Headers $H -ContentType 'application/json' -Body '{"title":"Smoke Test Course (edited)"}'
Write-Host "updated title:" $c2.title

$cos = Invoke-RestMethod -Method Put -Uri "$B/courses/$($c.id)/outcomes" -Headers $H -ContentType 'application/json' -Body '[{"code":"CO1","text":"Explain relational algebra"},{"code":"CO2","text":"Design normalised schemas"}]'
Write-Host "outcomes:" ($cos | ForEach-Object { $_.code }) -join ','

$list = Invoke-RestMethod -Uri "$B/courses?page_size=100" -Headers $H
Write-Host "courses total:" $list.total

# Multipart upload needs PowerShell 7 (-Form); verified through the frontend UI instead.
Invoke-RestMethod -Method Delete -Uri "$B/courses/$($c.id)" -Headers $H | Out-Null
try { Invoke-RestMethod -Uri "$B/courses/$($c.id)" -Headers $H } catch { Write-Host "after delete:" $_.Exception.Response.StatusCode.value__ }
