import {
  Document,
  Packer,
  Paragraph,
  HeadingLevel,
  TextRun,
  Table,
  TableRow,
  TableCell,
  WidthType,
} from 'docx'

function bulletList(items) {
  return items.map(
    (text) =>
      new Paragraph({
        text,
        bullet: { level: 0 },
      })
  )
}

function cell(text, opts = {}) {
  return new TableCell({
    width: { size: 33, type: WidthType.PERCENTAGE },
    children: [new Paragraph({ text, ...opts })],
  })
}

export async function exportReportAsWord(report) {
  const comparisonRows = [
    new TableRow({
      children: [
        cell('Criterion', { heading: HeadingLevel.HEADING_6 }),
        cell('Approach A', { heading: HeadingLevel.HEADING_6 }),
        cell('Approach B', { heading: HeadingLevel.HEADING_6 }),
      ],
    }),
    ...report.comparison_points.map(
      (p) =>
        new TableRow({
          children: [cell(p.criterion), cell(p.approach_a), cell(p.approach_b)],
        })
    ),
  ]

  const doc = new Document({
    sections: [
      {
        children: [
          new Paragraph({
            text: report.title,
            heading: HeadingLevel.TITLE,
          }),

          new Paragraph({ text: 'Overview', heading: HeadingLevel.HEADING_1 }),
          new Paragraph({ text: report.overview }),

          new Paragraph({ text: 'Comparison', heading: HeadingLevel.HEADING_1 }),
          new Table({ rows: comparisonRows, width: { size: 100, type: WidthType.PERCENTAGE } }),

          new Paragraph({
            text: 'Approach A — Pros & Cons',
            heading: HeadingLevel.HEADING_1,
            spacing: { before: 300 },
          }),
          ...bulletList(report.pros_approach_a.map((t) => `+ ${t}`)),
          ...bulletList(report.cons_approach_a.map((t) => `- ${t}`)),

          new Paragraph({
            text: 'Approach B — Pros & Cons',
            heading: HeadingLevel.HEADING_1,
            spacing: { before: 300 },
          }),
          ...bulletList(report.pros_approach_b.map((t) => `+ ${t}`)),
          ...bulletList(report.cons_approach_b.map((t) => `- ${t}`)),

          new Paragraph({
            text: 'Recommendation',
            heading: HeadingLevel.HEADING_1,
            spacing: { before: 300 },
          }),
          new Paragraph({ text: report.recommendation }),

          new Paragraph({
            text: 'Sources',
            heading: HeadingLevel.HEADING_1,
            spacing: { before: 300 },
          }),
          ...report.sources.flatMap((s) => [
            new Paragraph({
              children: [new TextRun({ text: s.title, bold: true })],
            }),
            new Paragraph({ text: s.relevance }),
            new Paragraph({
              children: [new TextRun({ text: s.url, italics: true, color: '0F5D5A' })],
            }),
          ]),
        ],
      },
    ],
  })

  const blob = await Packer.toBlob(doc)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${report.title.slice(0, 60).replace(/[^\w\s-]/g, '')}.docx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
