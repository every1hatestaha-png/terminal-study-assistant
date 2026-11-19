$ErrorActionPreference = "Stop"
$Server = "https://terminal-study-assistant-khzr.vercel.app"
Write-Host ""
Write-Host "KHZR TERMINAL | Groq + Gemini" -ForegroundColor Cyan
Write-Host "Practice client. Type /exit to quit, /clear to reset history."
Write-Host ""
$Token = Read-Host "Access token"
if ([string]::IsNullOrWhiteSpace($Token)) {
    Write-Host "Access token is required." -ForegroundColor Red
    exit 1
}
$History = @()
while ($true) {
    $Question = Read-Host "You"
    if ($Question -eq "/exit" -or $Question -eq "/quit") { break }
    if ($Question -eq "/clear") { $History = @(); Write-Host "History cleared."; continue }
    if ($Question -eq "/help") {
        Write-Host "Enter a C++ OOP practice question. Commands: /clear, /exit, /help"
        continue
    }
    if ([string]::IsNullOrWhiteSpace($Question)) { continue }
    try {
        $Headers = @{
            Authorization = "Bearer $Token"
            "X-Study-Token" = $Token
        }
        $Body = @{
            question = $Question
            history = $History
        } | ConvertTo-Json -Depth 8
        $Result = Invoke-RestMethod -Uri "$Server/v1/ask" -Method Post -Headers $Headers -ContentType "application/json" -Body $Body -TimeoutSec 60
        if ([string]::IsNullOrWhiteSpace($Result.answer)) {
            Write-Host "The server returned an empty answer." -ForegroundColor Red
            continue
        }
        if ($Result.model) { Write-Host "[Provider: $($Result.model)]" -ForegroundColor DarkGray }
        Write-Host ""
        Write-Host "KHZR >" -ForegroundColor Green
        Write-Host $Result.answer
        Write-Host ""
        $History += @(
            @{ role = "user"; content = $Question.Substring(0, [Math]::Min(2000, $Question.Length)) },
            @{ role = "assistant"; content = ([string]$Result.answer).Substring(0, [Math]::Min(2000, ([string]$Result.answer).Length)) }
        )
        if ($History.Count -gt 8) { $History = @($History | Select-Object -Last 8) }
    }
    catch {
        $Status = $null
        if ($_.Exception.Response) { $Status = [int]$_.Exception.Response.StatusCode }
        switch ($Status) {
            401 { Write-Host "Access token incorrect." -ForegroundColor Red }
            429 { Write-Host "Rate limit reached. Wait and retry." -ForegroundColor Red }
            502 { Write-Host "Both AI providers failed. Check server logs and provider keys." -ForegroundColor Red }
            503 { Write-Host "Server configuration incomplete. Check Vercel settings." -ForegroundColor Red }
            default { Write-Host "Request failed: $($_.Exception.Message)" -ForegroundColor Red }
        }
    }
}
Write-Host "KHZR closed."
