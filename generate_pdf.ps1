$outputPath = "c:\Users\PC\AI Support agent\AI_Support_Agent_Cost_Breakdown_5k.pdf"

$lines = @(
  "AI Support Agent - Cost Breakdown (5,000 Conversations/Month)",
  "",
  "Currency: USD",
  "Assumption: ~2,000 input + 600 output tokens per conversation",
  "",
  "METHOD A: Own CPU Server + External LLM API (Recommended now)",
  "Fixed Infra:",
  "- Vector DB / RAG storage: `$0 - `$80",
  "- DB + cache + backups + logging: `$30 - `$150",
  "- Monitoring/alerts: `$10 - `$60",
  "Fixed Subtotal: `$40 - `$290",
  "",
  "LLM Variable (for 5k convos):",
  "- Cost-efficient model tier: ~`$9",
  "- Higher-quality model tier: ~`$75",
  "- Smart routing (85% cheap + 15% premium): ~`$19",
  "",
  "Method A Total (5k):",
  "- Low-cost mode: ~$49 - `$299",
  "- Quality-focused mode: ~$115 - `$365",
  "- Practical blended target: ~$59 - `$309",
  "",
  "METHOD B: Own CPU Server + Rented Cloud GPU Inference",
  "GPU + Serving Stack:",
  "- Small cloud GPU (L4/A10 class): `$250 - `$700",
  "- Serving overhead + storage/network: `$50 - `$200",
  "- Monitoring + ops: `$20 - `$80",
  "GPU Stack Subtotal: `$320 - `$980",
  "",
  "Shared Infra (same as Method A fixed): `$40 - `$290",
  "Optional premium API fallback (5-15%): `$20 - `$300",
  "",
  "Method B Total (5k): ~$380 - `$1,570",
  "",
  "Conclusion:",
  "- At 5k conversations/month, Method A is usually much cheaper.",
  "- Move to Method B when API costs stay high for multiple months.",
  "",
  "Prepared for portfolio planning - Monday, May 4, 2026"
)

function Escape-PdfText([string]$text) {
  $escaped = $text -replace "\\", "\\\\"
  $escaped = $escaped -replace "\(", "\\("
  $escaped = $escaped -replace "\)", "\\)"
  return $escaped
}

$escapedLines = $lines | ForEach-Object { Escape-PdfText $_ }
$contentLines = $escapedLines | ForEach-Object { "($_) Tj`nT*" }
$contentStream = "BT`n/F1 11 Tf`n50 780 Td`n$($contentLines -join '')`nET"
$contentLength = [Text.Encoding]::ASCII.GetByteCount($contentStream)

$header = "%PDF-1.4`n"
$obj1 = "1 0 obj`n<< /Type /Catalog /Pages 2 0 R >>`nendobj`n"
$obj2 = "2 0 obj`n<< /Type /Pages /Kids [3 0 R] /Count 1 >>`nendobj`n"
$obj3 = "3 0 obj`n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>`nendobj`n"
$obj4 = "4 0 obj`n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>`nendobj`n"
$obj5 = "5 0 obj`n<< /Length $contentLength >>`nstream`n$contentStream`nendstream`nendobj`n"

$objects = @($obj1, $obj2, $obj3, $obj4, $obj5)
$offsets = New-Object System.Collections.Generic.List[int]

$builder = New-Object System.Text.StringBuilder
[void]$builder.Append($header)
$currentOffset = [Text.Encoding]::ASCII.GetByteCount($header)

foreach ($obj in $objects) {
  $offsets.Add($currentOffset)
  [void]$builder.Append($obj)
  $currentOffset += [Text.Encoding]::ASCII.GetByteCount($obj)
}

$xrefStart = $currentOffset
[void]$builder.Append("xref`n0 6`n")
[void]$builder.Append("0000000000 65535 f `n")
foreach ($offset in $offsets) {
  [void]$builder.Append(("{0:D10} 00000 n `n" -f $offset))
}
[void]$builder.Append("trailer`n<< /Size 6 /Root 1 0 R >>`nstartxref`n$xrefStart`n%%EOF")

[System.IO.File]::WriteAllText($outputPath, $builder.ToString(), [System.Text.Encoding]::ASCII)
Write-Output "PDF generated: $outputPath"
