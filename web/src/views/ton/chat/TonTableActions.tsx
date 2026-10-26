"use client";

import { useEffect, useState, type RefObject } from "react";
import { Button } from "@opal/components";
import { SvgCheck, SvgCopy, SvgSpreadsheetFile } from "@opal/icons";
import { COPY } from "@/lib/ton/copy";
import { downloadText, isNumericCell, toCsv } from "@/lib/ton/artifacts";

const TABLE = COPY.chat.table;

function readTable(table: HTMLTableElement): string[][] {
  return Array.from(table.rows).map((row) =>
    Array.from(row.cells).map((cell) => cell.innerText.trim())
  );
}

/** Copy (tab-separated, pastes into Excel) or download an answer's table. */
export default function TonTableActions({
  tableRef,
}: {
  tableRef: RefObject<HTMLTableElement | null>;
}) {
  const [copied, setCopied] = useState(false);
  // Money columns read right-aligned; runs on every render because the
  // table grows while the answer streams.
  useEffect(() => {
    const table = tableRef.current;
    if (!table) return;
    const body = Array.from(table.tBodies[0]?.rows ?? []);
    const width = table.rows[0]?.cells.length ?? 0;
    for (let column = 1; column < width; column++) {
      const filled = body
        .map((row) => row.cells[column]?.textContent?.trim() ?? "")
        .filter(Boolean);
      const numbers = filled.filter((cell) => isNumericCell(cell)).length;
      const numeric = numbers > 0 && numbers * 2 >= filled.length;
      for (const row of Array.from(table.rows))
        row.cells[column]?.classList.toggle("tn-num", numeric);
    }
  });
  return (
    <div className="tn-table-actions">
      <Button
        size="sm"
        prominence="tertiary"
        icon={copied ? SvgCheck : SvgCopy}
        tooltip={copied ? TABLE.copied : TABLE.copy}
        aria-label={TABLE.copy}
        onClick={() => {
          const table = tableRef.current;
          if (!table) return;
          void navigator.clipboard
            .writeText(
              readTable(table)
                .map((row) => row.join("\t"))
                .join("\n")
            )
            .then(() => {
              setCopied(true);
              setTimeout(() => setCopied(false), 1600);
            });
        }}
      />
      <Button
        size="sm"
        prominence="tertiary"
        icon={SvgSpreadsheetFile}
        tooltip={TABLE.excel}
        aria-label={TABLE.excel}
        onClick={() => {
          const table = tableRef.current;
          if (!table) return;
          const [head = [], ...rows] = readTable(table);
          downloadText("tabela-ton.csv", toCsv(head, rows));
        }}
      />
    </div>
  );
}
