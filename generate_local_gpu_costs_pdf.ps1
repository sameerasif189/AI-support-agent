# Rented GPU server cost PDF - formatted for client proposals
# Output: Rented_GPU_Bot_24x7_Client_Site_Costs.pdf

$outputPath = Join-Path $PSScriptRoot "Rented_GPU_Bot_24x7_Client_Site_Costs.pdf"
$pageWidth = 612
$pageHeight = 792

# Roles: title|subtitle|section|sub|body|bullet|money|warn|warnhdr|muted|tablehdr|tablerow|hr
$content = @(
  @{ Text = "ERP AI Support Agent"; Role = "title" },
  @{ Text = "Rented GPU Server - Monthly Costs (24/7)"; Role = "subtitle" },
  @{ Text = "Bot runs inference on a hired GPU VM (you do not buy the GPU card)."; Role = "muted" },
  @{ Text = "Client website embeds chat UI; backend calls your FastAPI + rented GPU API."; Role = "muted" },
  @{ Text = 'Currency: USD - Planning doc - May 8, 2026'; Role = "muted" },
  @{ Text = ""; Role = "body" },

  @{ Text = "DISCLAIMER"; Role = "warnhdr" },
  @{ Text = "Ranges are not quotes. GPU hourly rates change by provider, region, spot vs on-demand."; Role = "warn" },
  @{ Text = "Replace every band with a dated PDF quote or invoice from your chosen host."; Role = "warn" },
  @{ Text = ""; Role = "body" },

  @{ Text = "HOW THIS BOT SPENDS MONEY"; Role = "section" },
  @{ Text = "(1) Hired GPU machine - runs Ollama/vLLM 24/7 for chat completions."; Role = "bullet" },
  @{ Text = "(2) App + DB - FastAPI host (small VPS/VM) plus Neon Postgres for ERP + KB."; Role = "bullet" },
  @{ Text = "(3) Channels - WhatsApp / Slack provider fees if you use those routes."; Role = "bullet" },
  @{ Text = "(4) No retail GPU purchase - CapEx for cards is replaced by monthly GPU rent."; Role = "bullet" },
  @{ Text = ""; Role = "body" },

  @{ Text = "24/7 GPU RENT FORMULA"; Role = "section" },
  @{ Text = "Months use ~730 hours of continuous running."; Role = "sub" },
  @{ Text = 'Monthly_GPU_USD = hourly_rate_USD x 730'; Role = "money" },
  @{ Text = 'Example: $0.55/hr x 730 hr = $401.50/mo for one always-on instance.'; Role = "muted" },
  @{ Text = "Spot / interruptible VMs cost less but are risky for production chat."; Role = "muted" },
  @{ Text = ""; Role = "body" },

  @{ Text = "WHAT MODEL SIZE FITS EACH RENTED GPU (INFERENCE)"; Role = "section" },
  @{ Text = "Assumes ERP context + KB in prompt (this repo builds large prompts)."; Role = "muted" },
  @{ Text = "Quant Q4 = 4-bit weight quant (common on rented GPUs). FP16 = full precision."; Role = "muted" },
  @{ Text = ""; Role = "body" },
  @{ Text = "~8 GB VRAM - Edge / budget GPU"; Role = "sub" },
  @{ Text = "Typical: 7B instruct Q4 · tight context · risk OOM if prompt grows"; Role = "bullet" },
  @{ Text = "Example GPU classes: T4 16GB often priced low but shared; 8GB consumer tier tight"; Role = "muted" },
  @{ Text = ""; Role = "body" },
  @{ Text = "~16 GB VRAM - Practical production entry"; Role = "sub" },
  @{ Text = "7B FP16 or Q8 comfortably · 13B Q4 with moderate context"; Role = "bullet" },
  @{ Text = "Good match for support tone + grounding for most SMB ERP bots"; Role = "muted" },
  @{ Text = ""; Role = "body" },
  @{ Text = "~24 GB VRAM - Recommended balance"; Role = "sub" },
  @{ Text = "13B Q8 or FP16 · 8B very fast · 34B Q4 only if context kept short"; Role = "bullet" },
  @{ Text = "Fewer quantization artifacts vs 16 GB tier"; Role = "muted" },
  @{ Text = ""; Role = "body" },
  @{ Text = "~40-48 GB VRAM - Larger models"; Role = "sub" },
  @{ Text = "34B Q8 area · 70B Q4 possible but slower / batch 1"; Role = "bullet" },
  @{ Text = "Use when legal tone or multi-language quality needs extra capacity"; Role = "muted" },
  @{ Text = ""; Role = "body" },
  @{ Text = "~80 GB VRAM - Heavyweights"; Role = "sub" },
  @{ Text = "70B+ Q8 headroom · highest monthly rent"; Role = "bullet" },
  @{ Text = ""; Role = "body" },

  @{ Text = "INDICATIVE GPU RENT (24/7 MONTHLY FROM HOURLY BANDS)"; Role = "section" },
  @{ Text = 'Tier R1 Low | Example: older T4 / entry marketplace ~$0.25-0.45/hr'; Role = 'money' },
  @{ Text = '  -> ~$182 - $329 / mo at 730 hr'; Role = 'muted' },
  @{ Text = 'Tier R2 Mid | L4 / RTX-class cloud ~$0.50-0.90/hr'; Role = 'money' },
  @{ Text = '  -> ~$365 - $657 / mo'; Role = 'muted' },
  @{ Text = 'Tier R3 High | A100 partial / premium ~$1.20-2.50/hr'; Role = 'money' },
  @{ Text = '  -> ~$876 - $1,825 / mo'; Role = 'muted' },
  @{ Text = "Always paste your vendor row next to the tier you pick."; Role = "sub" },
  @{ Text = ""; Role = "body" },

  @{ Text = "OTHER MONTHLY COSTS (CLIENT SITE BOT STACK)"; Role = "section" },
  @{ Text = 'FastAPI + reverse proxy VPS (no GPU): typical $18 - $85/mo'; Role = 'money' },
  @{ Text = 'Neon Postgres (ERP + KB): free tier dev - prod often $0 - $70/mo'; Role = 'money' },
  @{ Text = 'TLS domain + DNS: often $0 - $20/mo baked into hosting'; Role = 'muted' },
  @{ Text = 'WhatsApp BSP / Slack (if used): illustrative $25 - $90/mo combined'; Role = 'money' },
  @{ Text = 'Monitoring / logs optional: $0 - $40/mo'; Role = 'muted' },
  @{ Text = ""; Role = "body" },

  @{ Text = "TOTAL MONTHLY EXAMPLES (24/7 BOT ON CLIENT SITE)"; Role = "section" },
  @{ Text = "Scenario A - Budget: R1 GPU + small VPS + Neon low + web only"; Role = "sub" },
  @{ Text = '  GPU ~$250 + VPS ~$25 + DB ~$20 = rough ~$295/mo (+channels if any)'; Role = 'money' },
  @{ Text = "Scenario B - Standard: R2 GPU + mid VPS + Neon prod + channels"; Role = "sub" },
  @{ Text = '  GPU ~$500 + VPS ~$45 + DB ~$35 + channels ~$50 = rough ~$630/mo'; Role = 'money' },
  @{ Text = "Scenario C - Premium: R3 GPU + better VPS + Neon + channels"; Role = "sub" },
  @{ Text = '  GPU ~$1,100 + VPS ~$70 + DB ~$55 + channels ~$70 = rough ~$1,295/mo'; Role = 'money' },
  @{ Text = "Add your exact GPU quote first - it dominates the bill."; Role = "warn" },
  @{ Text = ""; Role = "body" },

  @{ Text = "SUMMARY TABLE"; Role = "section" },
  @{ Text = "Line item                       Typical monthly USD (bands)"; Role = "tablehdr" },
  @{ Text = 'Rented GPU 24/7                 $180 - $1,825+'; Role = 'tablerow' },
  @{ Text = 'FastAPI / proxy host            $18 - $85'; Role = 'tablerow' },
  @{ Text = 'Postgres (Neon or managed)      $0 - $70'; Role = 'tablerow' },
  @{ Text = 'Messaging channels              $0 - $90'; Role = 'tablerow' },
  @{ Text = 'LLM API tokens                  $0 (local inference)'; Role = 'tablerow' },
  @{ Text = ""; Role = "body" },

  @{ Text = "APPENDIX"; Role = "section" },
  @{ Text = "A: Paste GPU provider quote (SKU, VRAM, hourly, region, date)."; Role = "body" },
  @{ Text = "B: Paste VPS and Neon invoices for the same month."; Role = "body" },
  @{ Text = ""; Role = "body" },
  @{ Text = "END"; Role = "muted" }
)

function Escape-PdfText([string]$text) {
  $escaped = $text -replace "\\", "\\\\"
  $escaped = $escaped -replace "\(", "\\("
  $escaped = $escaped -replace "\)", "\\)"
  return $escaped
}

function Get-Rgb([string]$role) {
  switch ($role) {
    "title"     { return "0.08 0.25 0.55" }
    "subtitle"  { return "0.15 0.40 0.70" }
    "section"   { return "0.82 0.38 0.10" }
    "sub"       { return "0.18 0.42 0.58" }
    "money"     { return "0.00 0.46 0.26" }
    "warnhdr"   { return "0.72 0.10 0.12" }
    "warn"      { return "0.52 0.14 0.12" }
    "muted"     { return "0.40 0.40 0.40" }
    "bullet"    { return "0.10 0.10 0.14" }
    "tablehdr"  { return "1 1 1" }
    "tablerow"  { return "0.10 0.10 0.14" }
    default     { return "0.08 0.08 0.10" }
  }
}

function Get-FontSize([string]$role) {
  switch ($role) {
    "title"    { return 17 }
    "subtitle" { return 11 }
    "section"  { return 10.5 }
    "warnhdr"  { return 10.5 }
    default    { return 9.5 }
  }
}

function Get-UseBold([string]$role) {
  return @("title", "subtitle", "section", "warnhdr", "tablehdr", "money", "sub") -contains $role
}

function Get-LeftMargin([string]$role) {
  if ($role -eq "bullet") { return 62 }
  return 48
}

function Build-LegendStream {
  $sb = New-Object System.Text.StringBuilder
  [void]$sb.AppendLine("q")
  [void]$sb.AppendLine("0.93 0.95 0.98 rg")
  [void]$sb.AppendLine("48 52 516 78 re f")
  [void]$sb.AppendLine("0.22 0.36 0.55 rg")
  [void]$sb.AppendLine("58 108 9 9 re f")
  [void]$sb.AppendLine("BT /F1 7.5 Tf 1 0 0 1 72 107 Tm 0.12 0.12 0.14 rg (Section titles - orange bar) Tj ET")
  [void]$sb.AppendLine("0 0.44 0.24 rg")
  [void]$sb.AppendLine("58 93 9 9 re f")
  [void]$sb.AppendLine("BT /F1 7.5 Tf 1 0 0 1 72 92 Tm 0.12 0.12 0.14 rg (Green bold = dollar math / tiers) Tj ET")
  [void]$sb.AppendLine("0.72 0.10 0.12 rg")
  [void]$sb.AppendLine("58 78 9 9 re f")
  [void]$sb.AppendLine("BT /F1 7.5 Tf 1 0 0 1 72 77 Tm 0.12 0.12 0.14 rg (Red = disclaimer / warnings) Tj ET")
  [void]$sb.AppendLine("Q")
  return $sb.ToString()
}

function Build-PageStreams($linesChunk, [int]$pageIndex) {
  $sb = New-Object System.Text.StringBuilder

  $leftDefault = 48
  $top = 744
  $lineStep = 12.5
  $extraAfterTitle = 4

  $y = $top
  $lineIndex = 0
  foreach ($item in $linesChunk) {
    $role = $item.Role
    $left = Get-LeftMargin $role
    $rgb = Get-Rgb $role
    $fs = Get-FontSize $role
    $bold = Get-UseBold $role
    $fontTag = if ($bold) { "/F2" } else { "/F1" }
    $text = Escape-PdfText $item.Text

    [void]$sb.AppendLine("q")
    if ($role -eq "section") {
      [void]$sb.AppendLine("1 0.93 0.82 rg")
      [void]$sb.AppendLine("$leftDefault $($y - 2) 516 14 re f")
    }
    elseif ($role -eq "tablehdr") {
      [void]$sb.AppendLine("0.16 0.34 0.58 rg")
      [void]$sb.AppendLine("$leftDefault $($y - 2) 516 13 re f")
    }
    elseif ($role -eq "tablerow" -and ($lineIndex % 2) -eq 1) {
      [void]$sb.AppendLine("0.94 0.96 1 rg")
      [void]$sb.AppendLine("$leftDefault $($y - 2) 516 12 re f")
    }
    [void]$sb.AppendLine("Q")

    $textRgb = if ($role -eq "tablehdr") { "1 1 1" } else { $rgb }

    [void]$sb.AppendLine("BT")
    [void]$sb.AppendLine("$fontTag $fs Tf")
    [void]$sb.AppendLine("1 0 0 1 $left $y Tm")
    [void]$sb.AppendLine("$textRgb rg")
    [void]$sb.AppendLine("($text) Tj")
    [void]$sb.AppendLine("ET")

    $y -= $lineStep
    if ($role -in @("title", "subtitle")) { $y -= $extraAfterTitle }
    $lineIndex++
  }

  $pn = $pageIndex + 1
  [void]$sb.AppendLine("BT /F1 8 Tf 1 0 0 1 548 772 Tm 0.55 0.55 0.55 rg (Page $pn) Tj ET")

  [void]$sb.AppendLine($(Build-LegendStream))

  return $sb.ToString()
}

$linesPerPage = 40

$pages = @()
for ($i = 0; $i -lt $content.Count; $i += $linesPerPage) {
  $end = [Math]::Min($i + $linesPerPage - 1, $content.Count - 1)
  $pages += ,($content[$i..$end])
}

$objects = New-Object System.Collections.Generic.List[string]
$objects.Add("1 0 obj`n<< /Type /Catalog /Pages 2 0 R >>`nendobj`n")

$pageCount = $pages.Count
$firstPageObj = 3
$firstFontObj = $firstPageObj + ($pageCount * 2)
$kidsRefs = @()

for ($p = 0; $p -lt $pageCount; $p++) {
  $pageObjNum = $firstPageObj + ($p * 2)
  $contentObjNum = $pageObjNum + 1
  $kidsRefs += "$pageObjNum 0 R"

  $contentStream = Build-PageStreams $pages[$p] $p
  $contentLength = [Text.Encoding]::ASCII.GetByteCount($contentStream)

  $pageObj = "$pageObjNum 0 obj`n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 $pageWidth $pageHeight] /Resources << /Font << /F1 $firstFontObj 0 R /F2 $($firstFontObj + 1) 0 R >> >> /Contents $contentObjNum 0 R >>`nendobj`n"
  $contentObj = "$contentObjNum 0 obj`n<< /Length $contentLength >>`nstream`n$contentStream`nendstream`nendobj`n"

  $objects.Add($pageObj)
  $objects.Add($contentObj)
}

$kids = $kidsRefs -join " "
$objects.Insert(1, "2 0 obj`n<< /Type /Pages /Kids [$kids] /Count $pageCount >>`nendobj`n")

$fontObjNum = $firstFontObj
$objects.Add("$fontObjNum 0 obj`n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>`nendobj`n")
$objects.Add("$($fontObjNum + 1) 0 obj`n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>`nendobj`n")

$header = "%PDF-1.4`n"
$builder = New-Object System.Text.StringBuilder
[void]$builder.Append($header)
$offsets = New-Object System.Collections.Generic.List[int]
$currentOffset = [Text.Encoding]::ASCII.GetByteCount($header)

foreach ($obj in $objects) {
  $offsets.Add($currentOffset)
  [void]$builder.Append($obj)
  $currentOffset += [Text.Encoding]::ASCII.GetByteCount($obj)
}

$objectCount = $objects.Count
$xrefStart = $currentOffset
[void]$builder.Append("xref`n0 " + ($objectCount + 1) + "`n")
[void]$builder.Append("0000000000 65535 f `n")
foreach ($offset in $offsets) {
  [void]$builder.Append(("{0:D10} 00000 n `n" -f $offset))
}
[void]$builder.Append("trailer`n<< /Size " + ($objectCount + 1) + " /Root 1 0 R >>`nstartxref`n$xrefStart`n%%EOF")

[System.IO.File]::WriteAllText($outputPath, $builder.ToString(), [System.Text.Encoding]::ASCII)
Write-Output "PDF generated: $outputPath"
