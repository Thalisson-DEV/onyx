"use client";

import { useState } from "react";
import { InputSingleSelect } from "@opal/components";

export interface Option {
  value: string;
  label: string;
  description?: string;
}

interface SelectProps {
  value: string;
  options: Option[];
  onChange: (value: string) => void;
  placeholder: string;
  label: string;
  error?: boolean;
  disabled?: boolean;
  /** Show a search row once the list is longer than this. */
  searchAbove?: number;
}

/** A single choice, with a search row when the list is long. */
export function Select({
  value,
  options,
  onChange,
  placeholder,
  label,
  error,
  disabled,
  searchAbove = 8,
}: SelectProps) {
  const [query, setQuery] = useState("");
  const needle = query
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
  const shown = needle
    ? options.filter((option) =>
        `${option.label} ${option.description ?? ""}`
          .normalize("NFD")
          .replace(/[̀-ͯ]/g, "")
          .toLowerCase()
          .includes(needle)
      )
    : options;
  return (
    <InputSingleSelect
      value={value || undefined}
      onValueChange={onChange}
      error={error}
      disabled={disabled}
      onOpenChange={(open) => {
        if (!open) setQuery("");
      }}
    >
      <InputSingleSelect.Trigger placeholder={placeholder} aria-label={label} />
      <InputSingleSelect.Content>
        {options.length > searchAbove && (
          <InputSingleSelect.Search
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar…"
          />
        )}
        {shown.map((option) => (
          <InputSingleSelect.Item
            key={option.value}
            value={option.value}
            description={option.description}
          >
            {option.label}
          </InputSingleSelect.Item>
        ))}
      </InputSingleSelect.Content>
    </InputSingleSelect>
  );
}

interface SegmentedProps<T extends string> {
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
  label: string;
}

export function Segmented<T extends string>({
  value,
  options,
  onChange,
  label,
}: SegmentedProps<T>) {
  return (
    <div
      className="ton-segmented flex-wrap w-fit max-w-full"
      role="group"
      aria-label={label}
    >
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          aria-pressed={value === option.value}
          className="ton-focusable ton-segment"
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
