$ErrorActionPreference = 'Stop'

$sourceDir = $PSScriptRoot
$domain = 'https://costo-vero.it'
$htmlFiles = @(Get-ChildItem -LiteralPath $sourceDir -Filter '*.html' -File -Recurse |
  Where-Object { $_.Name -ne '404.html' -and $_.FullName -notmatch '[\\/]\.publish-seo-' -and [IO.File]::ReadAllText($_.FullName) -notmatch '<meta\s+name="robots"\s+content="[^"]*noindex' } |
  Sort-Object FullName)

function Get-CanonicalPath([IO.FileInfo]$file) {
  $relative = $file.FullName.Substring($sourceDir.Length).TrimStart('\', '/') -replace '\\', '/'
  if ($relative -eq 'index.html') { return '/' }
  if ($relative -match '^(.*)/index\.html$') { return '/' + $Matches[1] + '/' }
  return '/' + $relative.Substring(0, $relative.Length - '.html'.Length)
}

$urls = foreach ($file in $htmlFiles) {
  $url = $domain + (Get-CanonicalPath $file)
  $lastmod = $file.LastWriteTimeUtc.ToString('yyyy-MM-dd')
  "  <url><loc>$url</loc><lastmod>$lastmod</lastmod></url>"
}

$xml = "<?xml version=`"1.0`" encoding=`"UTF-8`"?>`n<urlset xmlns=`"http://www.sitemaps.org/schemas/sitemap/0.9`">`n" + ($urls -join "`n") + "`n</urlset>`n"
[IO.File]::WriteAllText((Join-Path $sourceDir 'sitemap.xml'), $xml, [Text.UTF8Encoding]::new($false))
Write-Host "Sitemap aggiornata: $($htmlFiles.Count) pagine pubbliche." -ForegroundColor Green
