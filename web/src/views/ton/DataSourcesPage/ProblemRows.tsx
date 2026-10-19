"use client";

import useSWR from "swr";
import { Text } from "@opal/components";
import { cn } from "@opal/utils";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { COPY, formatNumber } from "@/lib/ton/copy";

const T = COPY.sources.detail.problems;

interface ProblemCell {
  column: string;
  header: string | null;
  value: string;
}

interface ProblemRow {
  code: string;
  sheet_name: string | null;
  row_number: number | null;
  column: string | null;
  cells: ProblemCell[];
}

interface ProblemRowsView {
  total: number;
  rows: ProblemRow[];
  cells_available: boolean;
}

/** The rows of one kind of import problem: where they are and what they hold. */
export default function ProblemRows({
  sourceKey,
  importId,
  code,
}: {
  sourceKey: string;
  importId: string;
  code: string;
}) {
  const { data, error, isLoading } = useSWR<ProblemRowsView>(
    `/api/ton/data-sources/${sourceKey}/imports/${importId}/problems?code=${encodeURIComponent(code)}`,
    errorHandlingFetcher
  );
  if (isLoading)
    return (
      <Text font="secondary-body" color="text-03">
        {T.loading}
      </Text>
    );
  if (error || !data)
    return (
      <Text font="secondary-body" color="status-error-05">
        {T.failed}
      </Text>
    );
  return (
    <div className="flex flex-col gap-2">
      {!data.cells_available && (
        <Text font="secondary-body" color="text-03">
          {T.cellsUnavailable}
        </Text>
      )}
      <div className="overflow-x-auto rounded-08 border border-01">
        <table className="ton-problem-rows w-full border-collapse">
          <thead>
            <tr>
              <th scope="col">{T.columns.place}</th>
              <th scope="col">{T.columns.column}</th>
              <th scope="col">{T.columns.content}</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, index) => {
              const flagged = row.cells.some((cell) => cell.column === row.column);
              return (
                <tr key={`${row.sheet_name}-${row.row_number}-${row.column}-${index}`}>
                  <td className="whitespace-nowrap">
                    <Text font="secondary-action" color="text-05">
                      {row.row_number
                        ? T.place(row.sheet_name ?? "—", row.row_number)
                        : (row.sheet_name ?? "—")}
                    </Text>
                  </td>
                  <td className="whitespace-nowrap">
                    <Text font="secondary-body" color="text-04">
                      {row.column ?? "—"}
                    </Text>
                  </td>
                  <td>
                    <span className="flex flex-wrap gap-1">
                      {row.column && !flagged && row.row_number && (
                        <span className="ton-problem-cell is-flagged">
                          {T.emptyCell(row.column)}
                        </span>
                      )}
                      {row.cells.map((cell) => (
                        <span
                          key={cell.column + (cell.header ?? "")}
                          className={cn(
                            "ton-problem-cell",
                            cell.column === row.column && "is-flagged"
                          )}
                          title={`${cell.column}${cell.header ? ` · ${cell.header}` : ""}`}
                        >
                          <b>{cell.header ?? cell.column}:</b> {cell.value}
                        </span>
                      ))}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {data.total > data.rows.length && (
        <Text font="secondary-body" color="text-03">
          {T.truncated(formatNumber(data.rows.length), formatNumber(data.total))}
        </Text>
      )}
    </div>
  );
}
