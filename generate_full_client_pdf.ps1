$outputPath = "c:\Users\PC\AI Support agent\ERP_AI_Support_Agent_Client_Ready_Proposal_5k.pdf"

$lines = @(
  "ERP AI Support Agent - Client Ready Proposal (5,000 Conversations/Month)",
  "Prepared for: Pakistan-based deployment",
  "Date: Monday, May 4, 2026",
  "",
  "1) Executive Summary",
  "This proposal presents a business-ready AI support system for ERP workflows.",
  "Recommended approach: CPU production server + external LLM API + RAG + human handoff.",
  "Goal: Automate repetitive support requests with reliable quality and controlled cost.",
  "",
  "2) Outcome-Focused Project Positioning",
  "Project Title: AI Customer Support Agent for ERP-enabled SaaS (Automates 60-80% Queries)",
  "Problem: Repetitive support tickets increase response time and support cost.",
  "Solution: LLM + retrieval + ERP tool-calling + escalation logic for production support.",
  "",
  "3) Hardware-Aware Deployment Strategy",
  "Production Server: i7 12th Gen, 32GB RAM (CPU only)",
  "- Host .NET API, orchestration, auth, ERP connectors, logging, ticketing.",
  "- Run retrieval layer and session/memory store.",
  "Development Workstation: Ryzen 5600X, 32GB RAM, RTX 5060 Ti 16GB",
  "- Local model testing, prompt tuning, staging experiments, regression checks.",
  "",
  "4) Target Architecture",
  "User -> Web/WhatsApp/Slack -> .NET Support API -> Intent Router",
  "Intent Router -> RAG Retrieval (pgvector/Pinecone) -> LLM API -> Response",
  "Intent Router -> ERP Tool Connectors (order, invoice, ticket, account)",
  "Low confidence/sensitive -> Human handoff with transcript summary",
  "",
  "5) Feature Set (Client-facing)",
  "- Conversational AI with contextual responses",
  "- Knowledge base retrieval (PDFs, docs, FAQs, SOPs)",
  "- ERP integration via secure backend tool calls",
  "- Session memory and conversation continuity",
  "- Human handoff and ticket creation",
  "- Multi-channel support: website, WhatsApp, Slack",
  "",
  "6) Exact Cost Breakdown (5,000 Conversations/Month, USD)",
  "Routing policy: 85% low-cost model + 15% premium fallback",
  "Conversation assumption: ~2,000 input + 600 output tokens per conversation",
  "",
  "A. Core Infrastructure (Monthly)",
  "- App hosting (API + workers): $35",
  "- Managed Postgres (app + session + audit): $25",
  "- Vector retrieval storage/index (entry tier): $20",
  "- Monitoring/logging/alerts: $15",
  "- Backup/object storage: $10",
  "Infrastructure subtotal: $105",
  "",
  "B. LLM Inference (Monthly)",
  "- Low-cost model traffic (85% share): $42",
  "- Premium fallback traffic (15% share): $78",
  "LLM subtotal: $120",
  "",
  "C. Channel Costs (Monthly)",
  "- Website chat channel: $0 (included in app)",
  "- WhatsApp messaging + provider fees: $32",
  "- Slack app operations (bot + webhook ops): $8",
  "Channel subtotal: $40",
  "",
  "D. Total Exact Monthly Cost",
  "Total Monthly Cost = Infrastructure ($105) + LLM ($120) + Channels ($40)",
  "Final Total: $265 / month",
  "Cost per conversation: $265 / 5000 = $0.053",
  "",
  "7) Performance Targets",
  "- Response latency target: under 3 seconds for common intents",
  "- Auto-resolution target: 60-80% repetitive queries",
  "- 24/7 availability with escalation fallback",
  "",
  "8) Rollout Plan",
  "Week 1: Intent mapping, knowledge ingestion, ERP tool wrappers",
  "Week 2: RAG + routing + web widget integration",
  "Week 3: WhatsApp and Slack channels, handoff workflows, observability",
  "Week 4: UAT, hardening, go-live, stakeholder demo video",
  "",
  "9) Risk Controls",
  "- RBAC and audit logs for all ERP actions",
  "- Prompt-injection filtering and retrieval sanitization",
  "- Confidence thresholds before automated actions",
  "",
  "10) Upgrade Trigger",
  "Move to dedicated cloud GPU inference only when monthly LLM cost remains high",
  "for multiple months and exceeds ROI threshold versus managed API inference.",
  "",
  "Client Recommendation",
  "For current scale (5k/month), this architecture is the best balance of quality,",
  "cost-efficiency, and deployment speed."
)

function Escape-PdfText([string]$text) {
  $escaped = $text -replace "\\", "\\\\"
  $escaped = $escaped -replace "\(", "\\("
  $escaped = $escaped -replace "\)", "\\)"
  return $escaped
}

$fontSize = 10
$pageWidth = 612
$pageHeight = 792
$leftMargin = 50
$topStart = 770
$lineStep = 12
$linesPerPage = 58

$escapedLines = $lines | ForEach-Object { Escape-PdfText $_ }

$pages = @()
for ($i = 0; $i -lt $escapedLines.Count; $i += $linesPerPage) {
  $end = [Math]::Min($i + $linesPerPage - 1, $escapedLines.Count - 1)
  $chunk = $escapedLines[$i..$end]
  $pages += ,$chunk
}

$objects = New-Object System.Collections.Generic.List[string]

# 1: Catalog, 2: Pages root
$objects.Add("1 0 obj`n<< /Type /Catalog /Pages 2 0 R >>`nendobj`n")

$pageCount = $pages.Count
$firstPageObj = 3
$firstFontObj = $firstPageObj + ($pageCount * 2)
$kidsRefs = @()

for ($p = 0; $p -lt $pageCount; $p++) {
  $pageObjNum = $firstPageObj + ($p * 2)
  $contentObjNum = $pageObjNum + 1
  $kidsRefs += "$pageObjNum 0 R"

  $contentLines = @()
  $contentLines += "BT"
  $contentLines += "/F1 $fontSize Tf"
  $contentLines += "$leftMargin $topStart Td"
  foreach ($line in $pages[$p]) {
    $contentLines += "($line) Tj"
    $contentLines += "T*"
  }
  $contentLines += "ET"
  $contentStream = ($contentLines -join "`n")
  $contentLength = [Text.Encoding]::ASCII.GetByteCount($contentStream)

  $pageObj = "$pageObjNum 0 obj`n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 $pageWidth $pageHeight] /Resources << /Font << /F1 $firstFontObj 0 R >> >> /Contents $contentObjNum 0 R >>`nendobj`n"
  $contentObj = "$contentObjNum 0 obj`n<< /Length $contentLength >>`nstream`n$contentStream`nendstream`nendobj`n"

  $objects.Add($pageObj)
  $objects.Add($contentObj)
}

$kids = $kidsRefs -join " "
$objects.Insert(1, "2 0 obj`n<< /Type /Pages /Kids [$kids] /Count $pageCount >>`nendobj`n")

$fontObjNum = $firstFontObj
$objects.Add("$fontObjNum 0 obj`n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>`nendobj`n")

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
