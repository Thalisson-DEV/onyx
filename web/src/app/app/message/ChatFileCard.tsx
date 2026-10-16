"use client";

import { Button, Text } from "@opal/components";
import {
  SvgArrowRight,
  SvgDownload,
  SvgFile,
  SvgFileChartPie,
  SvgFileText,
  SvgImage,
} from "@opal/icons";
import type { IconFunctionComponent } from "@opal/types";
import { COPY } from "@/lib/ton/copy";

const FILE = COPY.chatFile;

function extension(name: string): string {
  const dot = name.lastIndexOf(".");
  return dot === -1 ? "" : name.slice(dot + 1).toLowerCase();
}

function iconFor(ext: string): IconFunctionComponent {
  if (["xlsx", "xls", "csv"].includes(ext)) return SvgFileChartPie;
  if (["png", "jpg", "jpeg", "svg", "gif", "webp"].includes(ext))
    return SvgImage;
  if (["pdf", "docx", "txt", "md", "pptx"].includes(ext)) return SvgFileText;
  return SvgFile;
}

interface ChatFileCardProps {
  fileId: string;
  fileName: string;
  onOpen: () => void;
}

/**
 * A file the assistant generated (for example a PDF built in its Python
 * sandbox), shown like the TON report card: icon, name, kind, open and
 * download.
 */
export default function ChatFileCard({
  fileId,
  fileName,
  onOpen,
}: ChatFileCardProps) {
  const ext = extension(fileName);
  const Icon = iconFor(ext);
  const kind = FILE.kinds[ext] ?? FILE.fallbackKind;

  function download() {
    const anchor = document.createElement("a");
    anchor.href = `/api/chat/file/${encodeURIComponent(fileId)}`;
    anchor.download = fileName;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  }

  return (
    <div className="ton-result-card ton-file-card flex flex-wrap items-center gap-3 p-3">
      <span
        className="ton-icon-tile flex items-center justify-center w-9 h-9 shrink-0"
        data-tone="gold"
      >
        <Icon size={18} />
      </span>
      <span className="flex flex-1 min-w-0 flex-col">
        <span className="ton-file-card-name">
          <Text font="main-ui-action" color="text-05">
            {fileName}
          </Text>
        </span>
        <Text font="secondary-body" color="text-03">
          {`${kind} · ${FILE.generated}`}
        </Text>
      </span>
      <span className="flex gap-2 shrink-0">
        <Button size="md" rightIcon={SvgArrowRight} onClick={onOpen}>
          {FILE.open}
        </Button>
        <Button
          size="md"
          prominence="secondary"
          icon={SvgDownload}
          onClick={download}
        >
          {FILE.download}
        </Button>
      </span>
    </div>
  );
}
