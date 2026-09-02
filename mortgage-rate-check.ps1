$ErrorActionPreference = 'Stop'
$catalog = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'mortgage-rate-catalog.json') | ConvertFrom-Json
$errors = [System.Collections.Generic.List[string]]::new()
$today = Get-Date
if (-not $catalog.offers -or @($catalog.offers).Count -lt 1) { $errors.Add('Il catalogo tassi non contiene offerte.') }
foreach ($offer in @($catalog.offers)) {
  foreach ($field in @('id','bank','product','tan','taeg','rateType','conditions','sourceName','sourceUrl','checkedAtISO','expiresAtISO')) {
    if ($null -eq $offer.$field -or ($offer.$field -is [string] -and [string]::IsNullOrWhiteSpace($offer.$field))) { $errors.Add("$($offer.id): manca $field.") }
  }
  if ($offer.sourceUrl -notmatch '^https://') { $errors.Add("$($offer.id): fonte non valida.") }
  if ($offer.tan -le 0 -or $offer.taeg -le 0) { $errors.Add("$($offer.id): TAN e TAEG devono essere positivi.") }
  try { if (($today - [datetime]::ParseExact($offer.checkedAtISO,'yyyy-MM-dd',$null)).Days -gt 35) { $errors.Add("$($offer.id): verifica più vecchia di 35 giorni.") } } catch { $errors.Add("$($offer.id): checkedAtISO non valido.") }
  try { if ([datetime]::ParseExact($offer.expiresAtISO,'yyyy-MM-dd',$null) -lt $today.Date) { $errors.Add("$($offer.id): offerta scaduta.") } } catch { $errors.Add("$($offer.id): expiresAtISO non valido.") }
}
if ($errors.Count) { $errors | ForEach-Object { Write-Host "ERRORE: $_" -ForegroundColor Red }; exit 1 }
Write-Host "Catalogo tassi valido: $(@($catalog.offers).Count) offerte ufficiali verificabili." -ForegroundColor Green
