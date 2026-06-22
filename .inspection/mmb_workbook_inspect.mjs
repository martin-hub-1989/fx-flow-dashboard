import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const workbookPath = process.argv[2];
const outputDir = process.argv[3];
const input = await FileBlob.load(workbookPath);
const workbook = await SpreadsheetFile.importXlsx(input);

const sheetSummary = await workbook.inspect({
  kind: "sheet",
  include: "id,name",
  maxChars: 20000,
});

const workbookSummary = await workbook.inspect({
  kind: "workbook,definedName,drawing",
  maxChars: 30000,
  options: { maxResults: 500 },
});

await fs.mkdir(outputDir, { recursive: true });
await fs.writeFile(`${outputDir}/sheets.ndjson`, sheetSummary.ndjson);
await fs.writeFile(`${outputDir}/workbook.ndjson`, workbookSummary.ndjson);

const sheetLines = sheetSummary.ndjson
  .split("\n")
  .filter(Boolean)
  .map((line) => JSON.parse(line))
  .filter((row) => row.name && row.id);

const details = [];
for (const row of sheetLines) {
  const sheet = workbook.resolve(row.id);
  const used = sheet.getUsedRange();
  const usedAddress = used?.address ?? null;
  const region = usedAddress
    ? await workbook.inspect({
        kind: "region",
        sheetId: row.id,
        range: usedAddress,
        maxChars: 12000,
        tableMaxRows: 12,
        tableMaxCols: 16,
        tableMaxCellChars: 120,
      })
    : null;
  const formulas = usedAddress
    ? await workbook.inspect({
        kind: "formula",
        sheetId: row.id,
        range: usedAddress,
        maxChars: 20000,
        options: { maxResults: 300 },
      })
    : null;
  const drawings = await workbook.inspect({
    kind: "drawing",
    sheetId: row.id,
    maxChars: 20000,
    options: { maxResults: 300 },
  });

  details.push({
    id: row.id,
    name: row.name,
    usedAddress,
    region: region?.ndjson ?? "",
    formulas: formulas?.ndjson ?? "",
    drawings: drawings.ndjson,
  });
}

await fs.writeFile(
  `${outputDir}/details.json`,
  JSON.stringify(details, null, 2),
);

console.log(JSON.stringify({
  sheets: sheetLines.map(({ id, name }) => ({ id, name })),
  detailCount: details.length,
  outputDir,
}, null, 2));
