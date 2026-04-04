$templateFile = ".env.example"
$outputFile = ".env"

if (-not (Test-Path $templateFile)) {
    Write-Error "Template file $templateFile not found!"
    exit
}

function Get-SecureSecret([int]$length = 32) {
    $bytes = New-Object Byte[] $length
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($bytes)
    return [Convert]::ToBase64String($bytes).Replace('+', '-').Replace('/', '_').TrimEnd('=')
}

$postgres_password = ""

$content = Get-Content $templateFile | ForEach-Object {
    # Регулярное выражение для поиска ключей
    if ($_ -match "^(?<key>[A-Z0-9_]+)=\s*(?<value>.*)$") {
        $key = $Matches.key
        $val = $Matches.value

        if ([string]::IsNullOrWhiteSpace($val) -or $val -eq "generate") {
            $secret = Get-SecureSecret
            Write-Host "Generating secret for: $key" -ForegroundColor Cyan
            "$key=$secret"
            if ($key -eq "POSTGRES_PASSWORD") {
                $postgres_password = $secret
            }
        } elseif ($key -like "*_DATABASE_URL") {
            $secret = $val.Substring(0, 30) + $postgres_password + $val.Substring(36)
            "$key=$secret"
        } else {
            $_ 
        }
    } else {
        $_ 
    }
}

# Сохраняем в UTF8 без BOM (стандарт для .env)
[System.IO.File]::WriteAllLines((Convert-Path -Path "./.env"), $content)
# Или просто: $content | Out-File -FilePath $outputFile -Encoding utf8

Write-Host "Success: $outputFile has been created!" -ForegroundColor Green

docker-compose up