"use client";

import { Button, Text } from "@opal/components";
import { SvgPlus } from "@opal/icons";
import {
  CLASSIFICATION_COPY,
  type ClassificationTable,
} from "@/lib/ton/classification";

const COPY = CLASSIFICATION_COPY.natures;

export default function NaturesTab({
  table,
  onCreate,
}: {
  table: ClassificationTable;
  onCreate: () => void;
}) {
  const groups = [
    ...table.groups.map((group) => group.label),
    ...Array.from(
      new Set(
        table.natures
          .filter((item) => !item.dre_group_code)
          .map((item) => item.dre_group)
      )
    ),
  ];
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Text as="p" font="secondary-body" color="text-03">
          {COPY.intro}
        </Text>
        <span className="shrink-0">
          <Button icon={SvgPlus} onClick={onCreate}>
            {COPY.create}
          </Button>
        </span>
      </div>
      <div className="ton-card overflow-x-auto">
        <table className="ton-statement ton-classification-grid w-full min-w-[560px] border-collapse">
          <thead>
            <tr>
              <th scope="col">{COPY.columns.nature}</th>
              <th scope="col">{COPY.columns.group}</th>
              <th scope="col" data-numeric>
                {COPY.columns.accounts}
              </th>
            </tr>
          </thead>
          <tbody>
            {groups.map((label) =>
              table.natures
                .filter((item) => item.dre_group === label)
                .map((item) => (
                  <tr key={item.account_id}>
                    <th scope="row">
                      <Text font="secondary-action" color="text-05">
                        {item.natureza}
                      </Text>
                    </th>
                    <td>
                      <Text font="secondary-body" color="text-04">
                        {item.dre_group}
                      </Text>
                    </td>
                    <td data-numeric>
                      <Text font="secondary-body" color="text-05">
                        {String(item.accounts)}
                      </Text>
                    </td>
                  </tr>
                ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
