"use client";

import { useMemo } from "react";
import { Text } from "@opal/components";
import { COPY } from "@/lib/ton/copy";
import { buildDataPreview } from "@/lib/ton/data-preview";
import type { Json } from "@/lib/ton/work-log";

export interface DataPreviewViewProps {
  data: Json | undefined;
}

/** What a query read, as a small table or a list of labelled values. */
export default function DataPreviewView({ data }: DataPreviewViewProps) {
  const preview = useMemo(() => buildDataPreview(data), [data]);
  if (!preview) {
    return (
      <div className="ton-preview">
        <Text font="secondary-body" color="text-03">
          {COPY.work.data.empty}
        </Text>
      </div>
    );
  }
  const { fields, table } = preview;
  return (
    <div className="ton-preview">
      {fields.length > 0 && (
        <dl className="ton-preview-fields">
          {fields.map((field) => (
            <div key={field.label} className="contents">
              <dt>
                <Text font="secondary-body" color="text-03">
                  {field.label}
                </Text>
              </dt>
              <dd>
                <Text font="secondary-body" color="text-05">
                  {field.value}
                </Text>
              </dd>
            </div>
          ))}
        </dl>
      )}
      {table && (
        <div className="ton-preview-table-wrap">
          <table className="ton-preview-table">
            <thead>
              <tr>
                {table.columns.map((column) => (
                  <th
                    key={column.key}
                    scope="col"
                    data-numeric={column.numeric || undefined}
                  >
                    <Text font="secondary-action" color="text-03">
                      {column.label}
                    </Text>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.rows.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {row.map((cell, cellIndex) => (
                    <td
                      key={cellIndex}
                      data-numeric={
                        table.columns[cellIndex]?.numeric || undefined
                      }
                    >
                      <Text
                        font="secondary-body"
                        color={cellIndex === 0 ? "text-05" : "text-04"}
                      >
                        {cell}
                      </Text>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {table && table.total > table.rows.length && (
        <Text font="secondary-body" color="text-03">
          {COPY.work.data.showing(table.rows.length, table.total)}
        </Text>
      )}
    </div>
  );
}
