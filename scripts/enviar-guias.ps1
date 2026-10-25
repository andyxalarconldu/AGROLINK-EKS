$url = "http://a34d5348244ad4d32b45239e0a9f4f31-244711681.us-east-1.elb.amazonaws.com/despachos"
$exitosas = 0

Write-Host "Iniciando envio de 40 guias al ELB..." -ForegroundColor Cyan

1..40 | ForEach-Object {
    $bodega = "BOD-0$($_ % 3 + 1)"
    $body = @{
        id_centro_acopio = $bodega
        destino = "Mercado Mayorista Quito"
        id_transportista = "TRANS-001"
        producto = "papa"
        cantidad_kg = 10
    } | ConvertTo-Json

    try {
        $res = Invoke-WebRequest -Uri $url -Method Post -Body $body -ContentType "application/json" -UseBasicParsing
        if ($res.StatusCode -eq 202 -or $res.StatusCode -eq 200) {
            $exitosas++
            Write-Host "Guia $_ enviada a $bodega (HTTP $($res.StatusCode))" -ForegroundColor Green
        }
    } catch {
        Write-Host "Error enviando guia $_" -ForegroundColor Red
    }
    Start-Sleep -Milliseconds 1500
}

Write-Host "`nTOTAL ACEPTADAS (202): $exitosas" -ForegroundColor Yellow