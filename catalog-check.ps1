$ErrorActionPreference = 'Stop'

$catalogPath = Join-Path $PSScriptRoot 'offers.json'
$catalog = Get-Content -Raw -LiteralPath $catalogPath | ConvertFrom-Json
$offers = if ($catalog.offers) { @($catalog.offers) } else { @($catalog) }
$requiredFields = @('id', 'brand', 'model', 'aliases', 'match', 'title', 'type', 'payment', 'months', 'downPayment', 'finalPayment', 'contractKm', 'included', 'profile', 'sourceName', 'sourceUrl', 'checkedAtISO', 'checkedAt', 'conditions')
$errors = [System.Collections.Generic.List[string]]::new()
$warnings = [System.Collections.Generic.List[string]]::new()
$seenIds = [System.Collections.Generic.HashSet[string]]::new()

if (@($offers).Count -eq 0) { $errors.Add('Il catalogo non contiene offerte.') }

foreach ($offer in @($offers)) {
  $name = if ($offer.title) { $offer.title } else { '(offerta senza titolo)' }
  foreach ($field in $requiredFields) {
    if ($null -eq $offer.$field -or ($offer.$field -is [string] -and [string]::IsNullOrWhiteSpace($offer.$field))) {
      $errors.Add("${name}: manca '$field'.")
    }
  }
  if ($offer.id -and -not $seenIds.Add($offer.id)) { $errors.Add("ID duplicato: $($offer.id).") }
  if ($offer.aliases -and @($offer.aliases).Count -eq 0) { $errors.Add("${name}: aliases non può essere vuoto.") }
  if ($offer.type -notin @('finance', 'rental')) { $errors.Add("${name}: type deve essere finance o rental.") }
  foreach ($field in @('payment', 'months', 'downPayment', 'finalPayment', 'contractKm')) {
    if ($offer.$field -lt 0) { $errors.Add("${name}: '$field' non può essere negativo.") }
  }
  if ($offer.months -lt 1) { $errors.Add("${name}: servono almeno 1 mese.") }
  if ($offer.sourceUrl -and $offer.sourceUrl -notmatch '^https://') { $errors.Add("${name}: sourceUrl deve iniziare con https://.") }
  try {
    $checked = [datetime]::ParseExact($offer.checkedAtISO, 'yyyy-MM-dd', [cultureinfo]::InvariantCulture)
    if (((Get-Date) - $checked).Days -gt 45) { $warnings.Add("${name}: verifica più vecchia di 45 giorni ($($offer.checkedAt)).") }
  } catch {
    $errors.Add("${name}: checkedAtISO deve essere nel formato yyyy-MM-dd.")
  }
}

if ($warnings.Count) {
  Write-Host 'Avvisi catalogo:' -ForegroundColor Yellow
  $warnings | ForEach-Object { Write-Host "- $_" -ForegroundColor Yellow }
}
if ($errors.Count) {
  Write-Host 'Errori catalogo:' -ForegroundColor Red
  $errors | ForEach-Object { Write-Host "- $_" -ForegroundColor Red }
  exit 1
}

Write-Host "Catalogo valido: $(@($offers).Count) offerta/e controllata/e." -ForegroundColor Green
