Write-Output '----UNMERGED'
git diff --name-only --diff-filter=U
Write-Output '----OUR-CN'
git grep -l 'export function cn' 1d66c20 -- frontend/src
Write-Output '----VARIANTS-USED'
git grep -h -o -E 'variant="[a-z]+"|size="[a-z]+"' MERGE_HEAD -- frontend/src/features/landing frontend/src/components/brand frontend/src/components/theme | Sort-Object -Unique
Write-Output '----CONTENT-ENTRY'
git grep -n -E 'APP_ENTRY_PATH|href:' MERGE_HEAD -- frontend/src/features/landing/content.ts
Write-Output '----OUR-ROUTER'
git show 1d66c20:frontend/src/router.tsx
Write-Output '----OUR-BTN-VARIANTS'
git show 1d66c20:frontend/src/components/ui/button.tsx | Select-String -Pattern "^\s+[a-z]+: '"
Write-Output '----THEIR-CARD-BADGE-EXPORTS'
git show MERGE_HEAD:frontend/src/components/ui/card.tsx | Select-String -Pattern 'export'
git show MERGE_HEAD:frontend/src/components/ui/badge.tsx | Select-String -Pattern "export|^\s+[a-z]+: '"
Write-Output '----OUR-CARD-BADGE-EXPORTS'
git show 1d66c20:frontend/src/components/ui/card.tsx | Select-String -Pattern 'export'
git show 1d66c20:frontend/src/components/ui/badge.tsx | Select-String -Pattern "export|^\s+[a-z]+: '"
