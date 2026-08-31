$ErrorActionPreference = 'Stop'

$sourceDir = $PSScriptRoot
$domain = 'https://costo-vero.it'
$issues = [System.Collections.Generic.List[string]]::new()
$htmlFiles = @(Get-ChildItem -LiteralPath $sourceDir -Filter '*.html' -File)
$indexableFiles = @($htmlFiles | Where-Object Name -ne '404.html')

function Add-Issue([string]$message) {
  $script:issues.Add($message)
}

function Expected-Url([IO.FileInfo]$file) {
  if ($file.Name -eq 'index.html') { return $domain }
  return "$domain/$($file.BaseName)"
}

foreach ($file in $htmlFiles) {
  $content = [IO.File]::ReadAllText($file.FullName)
  $titleCount = [regex]::Matches($content, '<title>[^<]+</title>', 'IgnoreCase').Count
  $h1Count = [regex]::Matches($content, '<h1\b', 'IgnoreCase').Count
  if ($titleCount -ne 1) { Add-Issue "$($file.Name): trovati $titleCount title" }
  if ($h1Count -ne 1) { Add-Issue "$($file.Name): trovati $h1Count h1" }

  if ($file.Name -eq '404.html') {
    if ($content -notmatch '<meta\s+name="robots"\s+content="noindex,follow"') {
      Add-Issue '404.html: manca robots noindex,follow'
    }
  } else {
    $descriptionCount = [regex]::Matches($content, '<meta\s+name="description"\s+content="[^"]+"', 'IgnoreCase').Count
    $canonicalTags = @([regex]::Matches($content, '<link\b[^>]*\brel="canonical"[^>]*>', 'IgnoreCase'))
    if ($descriptionCount -ne 1) { Add-Issue "$($file.Name): trovate $descriptionCount meta description" }
    if ($canonicalTags.Count -ne 1) {
      Add-Issue "$($file.Name): trovati $($canonicalTags.Count) canonical"
    } else {
      $href = [regex]::Match($canonicalTags[0].Value, '\bhref="([^"]+)"', 'IgnoreCase').Groups[1].Value.TrimEnd('/')
      if ($href -ne (Expected-Url $file)) { Add-Issue "$($file.Name): canonical inatteso $href" }
    }
    if ($content -match '<meta\s+name="robots"\s+content="[^"]*noindex') {
      Add-Issue "$($file.Name): pagina indicizzabile marcata noindex"
    }
  }

  foreach ($block in [regex]::Matches($content, '<script\b[^>]*type="application/ld\+json"[^>]*>([\s\S]*?)</script>', 'IgnoreCase')) {
    try { $null = $block.Groups[1].Value | ConvertFrom-Json }
    catch { Add-Issue "$($file.Name): JSON-LD non valido" }
  }
}

$sitemapPath = Join-Path $sourceDir 'sitemap.xml'
try { [xml]$sitemap = [IO.File]::ReadAllText($sitemapPath) }
catch { Add-Issue 'sitemap.xml: XML non valido'; $sitemap = $null }

if ($null -ne $sitemap) {
  $namespace = [Xml.XmlNamespaceManager]::new($sitemap.NameTable)
  $namespace.AddNamespace('s', 'http://www.sitemaps.org/schemas/sitemap/0.9')
  $sitemapUrls = @($sitemap.SelectNodes('//s:url/s:loc', $namespace) | ForEach-Object { $_.'#text'.TrimEnd('/') })
  $expectedUrls = @($indexableFiles | ForEach-Object { Expected-Url $_ })
  foreach ($url in $expectedUrls | Where-Object { $_ -notin $sitemapUrls }) { Add-Issue "sitemap.xml: URL mancante $url" }
  foreach ($url in $sitemapUrls | Where-Object { $_ -notin $expectedUrls }) { Add-Issue "sitemap.xml: URL senza pagina $url" }
  foreach ($duplicate in $sitemapUrls | Group-Object | Where-Object Count -gt 1) { Add-Issue "sitemap.xml: URL duplicata $($duplicate.Name)" }
  foreach ($lastmod in $sitemap.SelectNodes('//s:url/s:lastmod', $namespace)) {
    $parsed = [datetime]::MinValue
    if (-not [datetime]::TryParseExact($lastmod.InnerText, 'yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::None, [ref]$parsed)) {
      Add-Issue "sitemap.xml: lastmod non valido $($lastmod.InnerText)"
    }
  }
}

foreach ($file in $htmlFiles) {
  $content = [IO.File]::ReadAllText($file.FullName)
  foreach ($match in [regex]::Matches($content, '\bhref="([^"]+)"', 'IgnoreCase')) {
    $href = $match.Groups[1].Value
    if (-not $href.StartsWith('/') -or $href.StartsWith('//')) { continue }
    $path = ($href -split '[?#]')[0].Trim('/')
    if (-not $path) { continue }
    $directPath = Join-Path $sourceDir $path
    $htmlPath = "$directPath.html"
    if (-not (Test-Path -LiteralPath $directPath) -and -not (Test-Path -LiteralPath $htmlPath)) {
      Add-Issue "$($file.Name): link locale inesistente $href"
    }
  }
}

if ($issues.Count) {
  $issues | ForEach-Object { Write-Host "ERRORE: $_" -ForegroundColor Red }
  Write-Host "Controllo sito non superato: $($issues.Count) problemi." -ForegroundColor Red
  exit 1
}

Write-Host "Controllo sito superato: $($htmlFiles.Count) pagine, sitemap e link interni validi." -ForegroundColor Green
