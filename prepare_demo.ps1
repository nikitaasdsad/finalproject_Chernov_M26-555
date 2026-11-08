$ErrorActionPreference = "Stop"

$users = @(Get-Content ".\data\users.json" -Raw | ConvertFrom-Json)
$user = $users | Where-Object { $_.username -eq "demo_user" } | Select-Object -First 1

if ($null -eq $user) {
    Write-Host "Пользователь demo_user не найден" -ForegroundColor Red
    exit 1
}

$portfolios = @(Get-Content ".\data\portfolios.json" -Raw | ConvertFrom-Json)

$portfolio = $portfolios | Where-Object {
    [string]$_.user_id -eq [string]$user.user_id
} | Select-Object -First 1

if ($null -eq $portfolio) {
    Write-Host "Портфель пользователя не найден" -ForegroundColor Red
    exit 1
}

$wallets = [PSCustomObject]@{
    USD = [PSCustomObject]@{
        balance = 100000
    }
}

$portfolio | Add-Member -MemberType NoteProperty -Name "wallets" -Value $wallets -Force

$portfolios | ConvertTo-Json -Depth 10 | Set-Content ".\data\portfolios.json" -Encoding utf8

Write-Host "Баланс 100000 USD успешно добавлен пользователю demo_user" -ForegroundColor Green
