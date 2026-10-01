export type BlockerCategory =
  | "units"
  | "budget"
  | "reconciliation"
  | "actuals"
  | "other";

export const BLOCKER_CATEGORY_ORDER: BlockerCategory[] = [
  "units",
  "budget",
  "reconciliation",
  "actuals",
  "other",
];

/**
 * Groups a readiness blocker by business area. The closing API returns
 * pt-BR labels; readiness APIs return codes. Both are matched.
 */
export function blockerCategory(label: string): BlockerCategory {
  const value = label.toLowerCase();
  if (/concilia|reconcil/.test(value)) return "reconciliation";
  if (/or[cç]amento|dota[cç][aã]o|budget/.test(value)) return "budget";
  if (/realizado|actual/.test(value)) return "actuals";
  if (/unidade|unit/.test(value)) return "units";
  return "other";
}

export interface BlockerGroup {
  category: BlockerCategory;
  count: number;
  labels: string[];
}

export function groupBlockers(
  blockers: Record<string, number>
): BlockerGroup[] {
  const groups = new Map<BlockerCategory, BlockerGroup>();
  for (const [label, count] of Object.entries(blockers)) {
    if (count <= 0) continue;
    const category = blockerCategory(label);
    const group = groups.get(category) ?? { category, count: 0, labels: [] };
    group.count += count;
    group.labels.push(label);
    groups.set(category, group);
  }
  return BLOCKER_CATEGORY_ORDER.flatMap((category) => {
    const group = groups.get(category);
    return group ? [group] : [];
  });
}

export function totalBlockers(blockers: Record<string, number>): number {
  return Object.values(blockers).reduce((sum, count) => sum + count, 0);
}
