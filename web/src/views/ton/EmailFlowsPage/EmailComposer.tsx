"use client";

import { useEffect, useRef, useState } from "react";
import { EditorContent, Node, mergeAttributes, useEditor, type Editor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { Color, TextStyle } from "@tiptap/extension-text-style";
import TextAlign from "@tiptap/extension-text-align";
import Image from "@tiptap/extension-image";
import {
  Button,
  InputSingleSelect,
  InputTypeIn,
  Modal,
  Text,
} from "@opal/components";
import { SvgLink, SvgMail, SvgRefreshCw } from "@opal/icons";
import {
  EMAIL_FLOWS_API,
  EMAIL_FLOWS_COPY as COPY,
  assetUrl,
  sendJson,
  uploadAsset,
  type AssetView,
  type CatalogView,
  type FlowDefinition,
  type PreviewView,
  type SendEmailStep,
} from "@/lib/ton/emailFlows";

const GLYPHS = {
  bold: "B",
  italic: "I",
  underline: "U",
  strike: "S",
  h2: "T1",
  h3: "T2",
  bullet: "•",
  ordered: "1.",
  left: "⇤",
  center: "↔",
  right: "⇥",
};
const COLORS = ["#1f2937", "#1f6f43", "#b45309", "#b91c1c", "#1d4ed8", "#6b7280"];

/** Inline chip for a variable; stored as <span data-variable="nome">. */
const Variable = Node.create({
  name: "variable",
  group: "inline",
  inline: true,
  atom: true,
  selectable: true,
  addAttributes() {
    return {
      name: {
        default: "",
        parseHTML: (element: HTMLElement) => element.getAttribute("data-variable") ?? "",
        renderHTML: (attributes: { name: string }) => ({ "data-variable": attributes.name }),
      },
    };
  },
  parseHTML() {
    return [{ tag: "span[data-variable]" }];
  },
  renderHTML({ node, HTMLAttributes }) {
    return ["span", mergeAttributes(HTMLAttributes, { class: "ton-var-chip" }), `{${node.attrs.name}}`];
  },
});

function blockExtension(labels: Record<string, string>) {
  /** A data block the server fills when sending; stored as <div data-block>. */
  return Node.create({
    name: "dataBlock",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
      return {
        block: {
          default: "summary",
          parseHTML: (element: HTMLElement) => element.getAttribute("data-block") ?? "summary",
          renderHTML: (attributes: { block: string }) => ({ "data-block": attributes.block }),
        },
      };
    },
    parseHTML() {
      return [{ tag: "div[data-block]" }];
    },
    renderHTML({ node, HTMLAttributes }) {
      const label = labels[String(node.attrs.block)] ?? String(node.attrs.block);
      return ["div", mergeAttributes(HTMLAttributes, { class: "ton-block-chip" }), COPY.composer.blockPlaceholder(label)];
    },
  });
}

/** Images come from the asset library; stored with data-asset-id only. */
const AssetImage = Image.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      assetId: {
        default: null,
        parseHTML: (element: HTMLElement) => element.getAttribute("data-asset-id"),
        renderHTML: (attributes: { assetId: string | null }) =>
          attributes.assetId ? { "data-asset-id": attributes.assetId } : {},
      },
      src: {
        default: null,
        parseHTML: (element: HTMLElement) => {
          const id = element.getAttribute("data-asset-id");
          return id ? assetUrl(id) : element.getAttribute("src");
        },
      },
      width: {
        default: null,
        parseHTML: (element: HTMLElement) => element.getAttribute("width"),
        renderHTML: (attributes: { width: string | null }) =>
          attributes.width ? { width: attributes.width } : {},
      },
    };
  },
});

function ToolButton({
  label,
  glyph,
  active,
  onClick,
}: {
  label: string;
  glyph: string;
  active?: boolean;
  onClick: () => void;
}) {
  return (
    <Button size="sm" prominence={active ? "secondary" : "tertiary"} aria-label={label} tooltip={label} onClick={onClick}>
      {glyph}
    </Button>
  );
}

function Toolbar({
  editor,
  catalog,
  variables,
  blocks,
  onAssetAdded,
}: {
  editor: Editor;
  catalog: CatalogView;
  variables: [string, string][];
  blocks: string[];
  onAssetAdded: (asset: AssetView) => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const C = COPY.composer;
  const chain = () => editor.chain().focus();

  function insertImage(asset: AssetView) {
    chain().insertContent({ type: "image", attrs: { src: assetUrl(asset.id), assetId: asset.id } }).run();
  }

  return (
    <div className="ton-composer-toolbar">
      <ToolButton label={C.bold} glyph={GLYPHS.bold} active={editor.isActive("bold")} onClick={() => chain().toggleBold().run()} />
      <ToolButton label={C.italic} glyph={GLYPHS.italic} active={editor.isActive("italic")} onClick={() => chain().toggleItalic().run()} />
      <ToolButton label={C.underline} glyph={GLYPHS.underline} active={editor.isActive("underline")} onClick={() => chain().toggleUnderline().run()} />
      <ToolButton label={C.strike} glyph={GLYPHS.strike} active={editor.isActive("strike")} onClick={() => chain().toggleStrike().run()} />
      <span className="ton-composer-sep" />
      <ToolButton label={C.h2} glyph={GLYPHS.h2} active={editor.isActive("heading", { level: 2 })} onClick={() => chain().toggleHeading({ level: 2 }).run()} />
      <ToolButton label={C.h3} glyph={GLYPHS.h3} active={editor.isActive("heading", { level: 3 })} onClick={() => chain().toggleHeading({ level: 3 }).run()} />
      <ToolButton label={C.bullet} glyph={GLYPHS.bullet} active={editor.isActive("bulletList")} onClick={() => chain().toggleBulletList().run()} />
      <ToolButton label={C.ordered} glyph={GLYPHS.ordered} active={editor.isActive("orderedList")} onClick={() => chain().toggleOrderedList().run()} />
      <span className="ton-composer-sep" />
      <ToolButton label={C.alignLeft} glyph={GLYPHS.left} active={editor.isActive({ textAlign: "left" })} onClick={() => chain().setTextAlign("left").run()} />
      <ToolButton label={C.alignCenter} glyph={GLYPHS.center} active={editor.isActive({ textAlign: "center" })} onClick={() => chain().setTextAlign("center").run()} />
      <ToolButton label={C.alignRight} glyph={GLYPHS.right} active={editor.isActive({ textAlign: "right" })} onClick={() => chain().setTextAlign("right").run()} />
      <span className="ton-composer-sep" />
      <span className="ton-composer-colors" aria-label={C.color}>
        {COLORS.map((color) => (
          <button
            key={color}
            type="button"
            className="ton-composer-swatch ton-focusable"
            style={{ background: color }}
            aria-label={`${C.color} ${color}`}
            onClick={() => chain().setColor(color).run()}
          />
        ))}
      </span>
      <Button
        size="sm"
        prominence="tertiary"
        icon={SvgLink}
        aria-label={C.link}
        tooltip={C.link}
        onClick={() => {
          const href = window.prompt(C.linkPrompt, editor.getAttributes("link").href ?? "https://");
          if (href === null) return;
          if (href === "") chain().unsetLink().run();
          else chain().setLink({ href }).run();
        }}
      />
      <span className="ton-composer-sep" />
      <div className="min-w-[9rem]">
        <InputSingleSelect
          value=""
          onValueChange={(name) => name && chain().insertContent({ type: "variable", attrs: { name } }).insertContent(" ").run()}
        >
          <InputSingleSelect.Trigger aria-label={C.variable} placeholder={C.variable} />
          <InputSingleSelect.Content>
            {variables.map(([name, description]) => (
              <InputSingleSelect.Item key={name} value={name}>
                {`{${name}} · ${description}`}
              </InputSingleSelect.Item>
            ))}
          </InputSingleSelect.Content>
        </InputSingleSelect>
      </div>
      <div className="min-w-[10rem]">
        <InputSingleSelect
          value=""
          onValueChange={(block) => block && chain().insertContent({ type: "dataBlock", attrs: { block } }).run()}
        >
          <InputSingleSelect.Trigger aria-label={C.block} placeholder={C.block} />
          <InputSingleSelect.Content>
            {blocks.map((block) => (
              <InputSingleSelect.Item key={block} value={block}>
                {catalog.blocks[block] ?? block}
              </InputSingleSelect.Item>
            ))}
          </InputSingleSelect.Content>
        </InputSingleSelect>
      </div>
      <div className="min-w-[9rem]">
        <InputSingleSelect
          value=""
          onValueChange={(value) => {
            if (value === "__upload") {
              fileRef.current?.click();
              return;
            }
            const asset = catalog.assets.find((item) => item.id === value);
            if (asset) insertImage(asset);
          }}
        >
          <InputSingleSelect.Trigger aria-label={C.image} placeholder={C.image} />
          <InputSingleSelect.Content>
            {catalog.assets.map((asset) => (
              <InputSingleSelect.Item key={asset.id} value={asset.id}>
                {asset.name}
              </InputSingleSelect.Item>
            ))}
            <InputSingleSelect.Item value="__upload">{C.upload}</InputSingleSelect.Item>
          </InputSingleSelect.Content>
        </InputSingleSelect>
      </div>
      <input
        ref={fileRef}
        type="file"
        accept="image/png,image/jpeg,image/gif"
        hidden
        onChange={async (event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (!file) return;
          const asset = await uploadAsset(file);
          onAssetAdded(asset);
          insertImage(asset);
        }}
      />
    </div>
  );
}

interface EmailComposerProps {
  open: boolean;
  step: SendEmailStep;
  definition: FlowDefinition;
  flowName: string;
  insideLoop: boolean;
  catalog: CatalogView;
  onAssetAdded: (asset: AssetView) => void;
  onChange: (step: SendEmailStep) => void;
  onClose: () => void;
}

export default function EmailComposer({
  open,
  step,
  definition,
  flowName,
  insideLoop,
  catalog,
  onAssetAdded,
  onChange,
  onClose,
}: EmailComposerProps) {
  const C = COPY.composer;
  const [preview, setPreview] = useState<PreviewView | null>(null);
  const [loading, setLoading] = useState(false);
  const stepRef = useRef(step);
  useEffect(() => {
    stepRef.current = step;
  }, [step]);
  const spec = catalog.triggers.find((item) => item.kind === definition.trigger.kind);
  const variables: [string, string][] = [
    ...Object.entries(catalog.system_variables),
    ...(insideLoop ? Object.entries(catalog.unit_variables) : []),
    ...definition.variables.map((variable): [string, string] => [variable.name, variable.value]),
  ];

  const editor = useEditor(
    {
      immediatelyRender: false,
      extensions: [
        StarterKit.configure({ link: { openOnClick: false, autolink: true } }),
        TextStyle,
        Color,
        TextAlign.configure({ types: ["heading", "paragraph"] }),
        AssetImage,
        Variable,
        blockExtension(catalog.blocks),
      ],
      content: step.body,
      editorProps: { attributes: { class: "ton-composer-content" } },
      onUpdate: ({ editor: current }) => onChange({ ...stepRef.current, body: current.getHTML() }),
    },
    [step.id]
  );

  async function refresh() {
    setLoading(true);
    try {
      const result = await sendJson<PreviewView>(`${EMAIL_FLOWS_API}/preview`, {
        definition,
        step_id: step.id,
        flow_name: flowName,
      });
      setPreview(result);
    } catch (failure) {
      setPreview({
        step_id: step.id,
        unit: null,
        reason: failure instanceof Error ? failure.message : String(failure),
        item_count: 0,
        subject: null,
        html: null,
        to: [],
        cc: [],
        bcc: [],
        trace: [],
      });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (open) void refresh();
    // Refresh when the composer opens; later on demand.
  }, [open, step.id]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Modal open={open} onOpenChange={(value) => !value && onClose()}>
      <Modal.Content width="full" height="full">
        <Modal.Header icon={SvgMail} title={C.title} description={step.subject || undefined} onClose={onClose} />
        <Modal.Body twoTone={false}>
          <div className="ton-composer">
            <div className="ton-composer-main">
              <InputTypeIn
                aria-label={COPY.editor.subject}
                placeholder={COPY.editor.subject}
                value={step.subject}
                maxLength={200}
                onChange={(event) => onChange({ ...step, subject: event.target.value })}
              />
              {editor && (
                <Toolbar
                  editor={editor}
                  catalog={catalog}
                  variables={variables}
                  blocks={spec?.blocks ?? []}
                  onAssetAdded={onAssetAdded}
                />
              )}
              <div className="ton-composer-editor">
                <EditorContent editor={editor} />
              </div>
            </div>
            <div className="ton-composer-preview">
              <div className="flex items-center justify-between gap-2">
                <Text font="secondary-body" color="text-03">
                  {preview ? (preview.html ? C.previewOf(preview.item_count) : preview.reason) : ""}
                </Text>
                <Button size="sm" prominence="tertiary" icon={SvgRefreshCw} disabled={loading} onClick={refresh}>
                  {C.refresh}
                </Button>
              </div>
              {preview?.html && (
                <iframe
                  title={COPY.editor.previewTitle}
                  srcDoc={preview.html}
                  // No scripts; same origin only so the library images load with the session.
                  sandbox="allow-same-origin"
                  className="ton-composer-frame"
                />
              )}
            </div>
          </div>
        </Modal.Body>
        <Modal.Footer>
          <Button onClick={onClose}>{C.done}</Button>
        </Modal.Footer>
      </Modal.Content>
    </Modal>
  );
}
