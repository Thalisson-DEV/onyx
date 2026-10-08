"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { EditorContent, Node, mergeAttributes, useEditor, type Editor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { Color, TextStyle } from "@tiptap/extension-text-style";
import TextAlign from "@tiptap/extension-text-align";
import Image from "@tiptap/extension-image";
import { Button, InputSingleSelect, Modal, Popover, Text } from "@opal/components";
import { SvgBlocks, SvgLink, SvgMail, SvgRefreshCw, SvgZap } from "@opal/icons";
import {
  AUTOMATIONS_API,
  DESIGNER_COPY as D,
  send,
  type CatalogView,
  type Definition,
  type FlowNode,
  type PreviewResult,
} from "@/lib/ton/automations";
import { assetUrl, uploadAsset } from "@/lib/ton/emailFlows";
import { asText } from "@/lib/ton/automationTree";
import { describeExpression, dynamicGroups } from "@/views/ton/AutomationsPage/designer/dynamic";
import { DynamicPicker, ExpressionInput, type DynamicContext } from "@/views/ton/AutomationsPage/designer/fields";

const COLORS = ["#1f2937", "#1f6f43", "#b45309", "#b91c1c", "#1d4ed8", "#6b7280"];
const C = {
  bold: "Negrito",
  italic: "Itálico",
  underline: "Sublinhado",
  h2: "Título",
  h3: "Subtítulo",
  bullet: "Lista",
  ordered: "Lista numerada",
  left: "Alinhar à esquerda",
  center: "Centralizar",
  right: "Alinhar à direita",
  color: "Cor do texto",
  link: "Link",
  linkPrompt: "Endereço do link (vazio para remover)",
  block: "Bloco de dados",
  blockSource: "Lista do bloco",
  defaultSource: "Lista padrão do passo",
  image: "Imagem",
  upload: "Enviar imagem…",
  title: "Mensagem do e-mail",
  subject: "Assunto",
  refresh: "Atualizar prévia",
  done: "Concluir",
  blockOf: (label: string) => `▦ ${label} · preenchido com os dados ao enviar`,
};

function chipExtension(context: DynamicContext) {
  return Node.create({
    name: "dynamicChip",
    group: "inline",
    inline: true,
    atom: true,
    selectable: true,
    addAttributes() {
      return {
        expr: {
          default: "",
          parseHTML: (element: HTMLElement) => element.getAttribute("data-expr") ?? "",
          renderHTML: (attributes: { expr: string }) => ({ "data-expr": attributes.expr }),
        },
      };
    },
    parseHTML() {
      return [{ tag: "span[data-expr]" }];
    },
    renderHTML({ node, HTMLAttributes }) {
      return ["span", mergeAttributes(HTMLAttributes, { class: "ton-var-chip" }), `⚡ ${describeExpression(String(node.attrs.expr), context.definition, context.catalog)}`];
    },
  });
}

/** Legacy chips of converted e-mail flows ({semana}, {data}…). */
const LegacyVariable = Node.create({
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

function blockExtension(labels: Record<string, string>, context: DynamicContext) {
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
        source: {
          default: null,
          parseHTML: (element: HTMLElement) => element.getAttribute("data-source"),
          renderHTML: (attributes: { source: string | null }) => (attributes.source ? { "data-source": attributes.source } : {}),
        },
      };
    },
    parseHTML() {
      return [{ tag: "div[data-block]" }];
    },
    renderHTML({ node, HTMLAttributes }) {
      const label = labels[String(node.attrs.block)] ?? String(node.attrs.block);
      const source = node.attrs.source ? ` · ${describeExpression(String(node.attrs.source), context.definition, context.catalog)}` : "";
      return ["div", mergeAttributes(HTMLAttributes, { class: "ton-block-chip" }), C.blockOf(`${label}${source}`)];
    },
  });
}

const AssetImage = Image.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      assetId: {
        default: null,
        parseHTML: (element: HTMLElement) => element.getAttribute("data-asset-id"),
        renderHTML: (attributes: { assetId: string | null }) => (attributes.assetId ? { "data-asset-id": attributes.assetId } : {}),
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
        renderHTML: (attributes: { width: string | null }) => (attributes.width ? { width: attributes.width } : {}),
      },
    };
  },
});

function Tool({ label, glyph, active, onClick }: { label: string; glyph: string; active?: boolean; onClick: () => void }) {
  return (
    <Button size="sm" prominence={active ? "secondary" : "tertiary"} aria-label={label} tooltip={label} onClick={onClick}>
      {glyph}
    </Button>
  );
}

function Toolbar({ editor, catalog, context }: { editor: Editor; catalog: CatalogView; context: DynamicContext }) {
  const [dynamicOpen, setDynamicOpen] = useState(false);
  const [blockOpen, setBlockOpen] = useState(false);
  const [blockSource, setBlockSource] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const [assets, setAssets] = useState(catalog.assets);
  const chain = () => editor.chain().focus();
  const lists = useMemo(
    () =>
      dynamicGroups(context.definition, context.nodeId, context.catalog)
        .flatMap((group) => group.items.filter((item) => item.type === "array").map((item): [string, string] => [item.expression, `${group.title} › ${item.label}`])),
    [context]
  );

  return (
    <div className="ton-email-composer-toolbar">
      <Tool label={C.bold} glyph="B" active={editor.isActive("bold")} onClick={() => chain().toggleBold().run()} />
      <Tool label={C.italic} glyph="I" active={editor.isActive("italic")} onClick={() => chain().toggleItalic().run()} />
      <Tool label={C.underline} glyph="U" active={editor.isActive("underline")} onClick={() => chain().toggleUnderline().run()} />
      <span className="ton-email-composer-sep" />
      <Tool label={C.h2} glyph="T1" active={editor.isActive("heading", { level: 2 })} onClick={() => chain().toggleHeading({ level: 2 }).run()} />
      <Tool label={C.h3} glyph="T2" active={editor.isActive("heading", { level: 3 })} onClick={() => chain().toggleHeading({ level: 3 }).run()} />
      <Tool label={C.bullet} glyph="•" active={editor.isActive("bulletList")} onClick={() => chain().toggleBulletList().run()} />
      <Tool label={C.ordered} glyph="1." active={editor.isActive("orderedList")} onClick={() => chain().toggleOrderedList().run()} />
      <span className="ton-email-composer-sep" />
      <Tool label={C.left} glyph="⇤" active={editor.isActive({ textAlign: "left" })} onClick={() => chain().setTextAlign("left").run()} />
      <Tool label={C.center} glyph="↔" active={editor.isActive({ textAlign: "center" })} onClick={() => chain().setTextAlign("center").run()} />
      <Tool label={C.right} glyph="⇥" active={editor.isActive({ textAlign: "right" })} onClick={() => chain().setTextAlign("right").run()} />
      <span className="ton-email-composer-sep" />
      <span className="ton-email-composer-colors" aria-label={C.color}>
        {COLORS.map((color) => (
          <button key={color} type="button" className="ton-email-composer-swatch ton-focusable" style={{ background: color }} aria-label={`${C.color} ${color}`} onClick={() => chain().setColor(color).run()} />
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
      <span className="ton-email-composer-sep" />
      <Popover open={dynamicOpen} onOpenChange={setDynamicOpen}>
        <Popover.Trigger asChild>
          <Button size="sm" prominence="secondary" icon={SvgZap}>
            {D.dynamic}
          </Button>
        </Popover.Trigger>
        <Popover.Content width="lg" align="start">
          <DynamicPicker
            context={context}
            onPick={(expression) => {
              chain().insertContent({ type: "dynamicChip", attrs: { expr: expression } }).insertContent(" ").run();
              setDynamicOpen(false);
            }}
          />
        </Popover.Content>
      </Popover>
      <Popover open={blockOpen} onOpenChange={setBlockOpen}>
        <Popover.Trigger asChild>
          <Button size="sm" prominence="secondary" icon={SvgBlocks}>
            {C.block}
          </Button>
        </Popover.Trigger>
        <Popover.Content width="lg" align="start">
          <div className="flex flex-col gap-2 p-1">
            <Text font="secondary-action" color="text-04">
              {C.blockSource}
            </Text>
            <InputSingleSelect value={blockSource || "__default"} onValueChange={(value) => setBlockSource(value === "__default" ? "" : value)}>
              <InputSingleSelect.Trigger aria-label={C.blockSource} />
              <InputSingleSelect.Content>
                <InputSingleSelect.Item value="__default">{C.defaultSource}</InputSingleSelect.Item>
                {lists.map(([expression, label]) => (
                  <InputSingleSelect.Item key={expression} value={expression}>
                    {label}
                  </InputSingleSelect.Item>
                ))}
              </InputSingleSelect.Content>
            </InputSingleSelect>
            <div className="flex flex-col">
              {Object.entries(catalog.blocks).map(([block, label]) => (
                <button
                  key={block}
                  type="button"
                  className="ton-auto-dyn-item ton-focusable"
                  onClick={() => {
                    chain().insertContent({ type: "dataBlock", attrs: { block, source: blockSource || null } }).run();
                    setBlockOpen(false);
                  }}
                >
                  <span className="ton-auto-dyn-label">{label}</span>
                </button>
              ))}
            </div>
          </div>
        </Popover.Content>
      </Popover>
      <div className="min-w-[9rem]">
        <InputSingleSelect
          value=""
          onValueChange={(value) => {
            if (value === "__upload") {
              fileRef.current?.click();
              return;
            }
            const asset = assets.find((item) => item.id === value);
            if (asset) chain().insertContent({ type: "image", attrs: { src: assetUrl(asset.id), assetId: asset.id } }).run();
          }}
        >
          <InputSingleSelect.Trigger aria-label={C.image} placeholder={C.image} />
          <InputSingleSelect.Content>
            {assets.map((asset) => (
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
          setAssets((current) => [...current, { id: asset.id, name: asset.name }]);
          chain().insertContent({ type: "image", attrs: { src: assetUrl(asset.id), assetId: asset.id } }).run();
        }}
      />
    </div>
  );
}

interface EmailBodyEditorProps {
  open: boolean;
  node: FlowNode;
  definition: Definition;
  catalog: CatalogView;
  automationId: string | null;
  automationName: string;
  onChange: (params: Record<string, string>) => void;
  onClose: () => void;
}

export default function EmailBodyEditor({ open, node, definition, catalog, automationId, automationName, onChange, onClose }: EmailBodyEditorProps) {
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [loading, setLoading] = useState(false);
  const context: DynamicContext = useMemo(() => ({ definition, catalog, nodeId: node.id }), [definition, catalog, node.id]);
  const contextRef = useRef(context);
  const onChangeRef = useRef(onChange);
  useEffect(() => {
    contextRef.current = context;
    onChangeRef.current = onChange;
  });

  const editor = useEditor(
    {
      immediatelyRender: false,
      extensions: [
        StarterKit.configure({ link: { openOnClick: false, autolink: true } }),
        TextStyle,
        Color,
        TextAlign.configure({ types: ["heading", "paragraph"] }),
        AssetImage,
        LegacyVariable,
        chipExtension(contextRef.current),
        blockExtension(catalog.blocks, contextRef.current),
      ],
      content: asText(node.params.body),
      editorProps: { attributes: { class: "ton-email-composer-content" } },
      onUpdate: ({ editor: current }) => onChangeRef.current({ body: current.getHTML() }),
    },
    [node.id, open]
  );

  async function refresh() {
    setLoading(true);
    try {
      const result = await send<PreviewResult>(`${AUTOMATIONS_API}/preview`, {
        definition,
        node_id: node.id,
        automation_id: automationId,
        name: automationName,
      });
      setPreview(result);
    } catch (failure) {
      setPreview({ subject: null, html: null, reason: failure instanceof Error ? failure.message : String(failure) });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (open) void refresh();
  }, [open, node.id]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Modal open={open} onOpenChange={(value) => !value && onClose()}>
      <Modal.Content width="full" height="full">
        <Modal.Header icon={SvgMail} title={C.title} description={asText(node.params.subject) || undefined} onClose={onClose} />
        <Modal.Body twoTone={false}>
          <div className="ton-email-composer">
            <div className="ton-email-composer-main">
              <ExpressionInput
                value={asText(node.params.subject)}
                onChange={(subject) => onChange({ subject })}
                context={context}
                label={C.subject}
                placeholder={C.subject}
              />
              {editor && <Toolbar editor={editor} catalog={catalog} context={context} />}
              <div className="ton-email-composer-editor">
                <EditorContent editor={editor} />
              </div>
            </div>
            <div className="ton-email-composer-preview">
              <div className="flex items-center justify-between gap-2">
                <Text font="secondary-body" color="text-03">
                  {preview?.reason ?? ""}
                </Text>
                <Button size="sm" prominence="tertiary" icon={SvgRefreshCw} disabled={loading} onClick={refresh}>
                  {C.refresh}
                </Button>
              </div>
              {preview?.subject && (
                <Text font="main-ui-action" color="text-05">
                  {preview.subject}
                </Text>
              )}
              {preview?.html && <iframe title={D.previewTitle} srcDoc={preview.html} sandbox="allow-same-origin" className="ton-email-composer-frame" />}
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
