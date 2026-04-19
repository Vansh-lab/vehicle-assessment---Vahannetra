import type { DamageFinding, InspectionResult } from "@/types/domain";

function toTitle(value: string): string {
  return value
    .replace(/_/g, " ")
    .split(" ")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export async function downloadFallbackInspectionPdf(result: InspectionResult): Promise<void> {
  const { jsPDF } = await import("jspdf");
  const pdf = new jsPDF({ unit: "mm", format: "a4" });
  pdf.setFontSize(16);
  pdf.text("VahanNetra Inspection Report", 14, 14);

  pdf.setFontSize(10);
  pdf.text(`Inspection ID: ${result.inspectionId}`, 14, 22);
  pdf.text(`Vehicle: ${result.vehicle.plate} • ${result.vehicle.model} • ${result.vehicle.type}`, 14, 28);
  pdf.text(`Health Score: ${result.healthScore}`, 14, 34);
  pdf.text(`Triage: ${result.triageCategory}`, 14, 40);

  let y = 50;
  pdf.setFontSize(11);
  pdf.text("Detected Damages", 14, y);
  y += 6;

  result.findings.forEach((finding: DamageFinding, idx: number) => {
    if (y > 280) {
      pdf.addPage();
      y = 20;
    }
    const centerX = Math.round((finding.box[0] + finding.box[2]) / 2);
    const centerY = Math.round((finding.box[1] + finding.box[3]) / 2);
    const width = Math.round(Math.max(0, finding.box[2] - finding.box[0]));
    const height = Math.round(Math.max(0, finding.box[3] - finding.box[1]));

    pdf.setFontSize(9);
    pdf.text(
      `${idx + 1}. ${toTitle(finding.type)} | ${toTitle(finding.severity)} | Confidence ${Math.round(finding.confidence * 100)}%`,
      14,
      y,
    );
    y += 5;
    pdf.text(
      `Location: (${centerX}, ${centerY}) px • Box: ${width}x${height} px • Estimate: ₹${finding.estimateMin.toLocaleString()} - ₹${finding.estimateMax.toLocaleString()}`,
      14,
      y,
      { maxWidth: 182 },
    );
    y += 7;
  });

  pdf.setFontSize(8);
  pdf.text("Generated fallback client PDF (backend PDF unavailable).", 14, 290);
  pdf.save(`${result.inspectionId}.pdf`);
}
