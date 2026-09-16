/**
 * TON-VIS-005 — semantic file categories.
 *
 * `fileCategory` is the single answer to "what is this file?" for the composer
 * card, the file picker, the user-file modal and the project context panel. The
 * cases below are the ones that used to be decided four different ways, plus
 * the precedence rule that keeps a generic MIME type from overruling a name the
 * user can read.
 */
import {
  FILE_CATEGORY_LABEL_KEYS,
  FileCategory,
  fileCategory,
  fileCategoryIcon,
  isImageFile,
} from "@/lib/utils";

describe("fileCategory by MIME type", () => {
  test("resolves a spreadsheet", () => {
    expect(
      fileCategory(
        "resultado.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      )
    ).toBe(FileCategory.SPREADSHEET);
    expect(fileCategory("dados", "text/csv")).toBe(FileCategory.SPREADSHEET);
  });

  test("resolves a document", () => {
    expect(fileCategory("contrato", "application/pdf")).toBe(
      FileCategory.DOCUMENT
    );
  });

  test("resolves an image", () => {
    expect(fileCategory("captura", "image/png")).toBe(FileCategory.IMAGE);
  });

  test("resolves a presentation", () => {
    expect(
      fileCategory(
        "diretoria",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
      )
    ).toBe(FileCategory.PRESENTATION);
  });

  test("resolves an archive", () => {
    expect(fileCategory("lote", "application/zip")).toBe(FileCategory.ARCHIVE);
  });

  test("resolves audio and video from the MIME family alone", () => {
    // Neither extension is enumerated; the top-level type carries the category.
    expect(fileCategory("ata.flac", "audio/flac")).toBe(FileCategory.AUDIO);
    expect(fileCategory("vistoria.mkv", "video/x-matroska")).toBe(
      FileCategory.VIDEO
    );
  });

  test("ignores MIME parameters", () => {
    expect(fileCategory("dados", "text/csv;charset=utf-8")).toBe(
      FileCategory.SPREADSHEET
    );
  });
});

describe("fileCategory by extension", () => {
  test.each([
    ["resultado.xlsx", FileCategory.SPREADSHEET],
    ["resultado.xls", FileCategory.SPREADSHEET],
    ["resultado.csv", FileCategory.SPREADSHEET],
    ["resultado.ods", FileCategory.SPREADSHEET],
    ["contrato.pdf", FileCategory.DOCUMENT],
    ["contrato.doc", FileCategory.DOCUMENT],
    ["contrato.docx", FileCategory.DOCUMENT],
    ["notas.txt", FileCategory.DOCUMENT],
    ["notas.md", FileCategory.DOCUMENT],
    ["captura.png", FileCategory.IMAGE],
    ["captura.jpg", FileCategory.IMAGE],
    ["captura.jpeg", FileCategory.IMAGE],
    ["captura.gif", FileCategory.IMAGE],
    ["captura.webp", FileCategory.IMAGE],
    ["captura.svg", FileCategory.IMAGE],
    ["diretoria.ppt", FileCategory.PRESENTATION],
    ["diretoria.pptx", FileCategory.PRESENTATION],
    ["diretoria.odp", FileCategory.PRESENTATION],
    ["ata.mp3", FileCategory.AUDIO],
    ["ata.wav", FileCategory.AUDIO],
    ["ata.m4a", FileCategory.AUDIO],
    ["ata.ogg", FileCategory.AUDIO],
    ["vistoria.mp4", FileCategory.VIDEO],
    ["vistoria.mov", FileCategory.VIDEO],
    ["vistoria.webm", FileCategory.VIDEO],
    ["lote.zip", FileCategory.ARCHIVE],
    ["lote.rar", FileCategory.ARCHIVE],
    ["lote.7z", FileCategory.ARCHIVE],
    ["lote.tar", FileCategory.ARCHIVE],
    ["lote.gz", FileCategory.ARCHIVE],
  ])("resolves %s", (name, expected) => {
    expect(fileCategory(name)).toBe(expected);
  });
});

describe("fileCategory precedence", () => {
  test("a generic MIME type does not overrule a known extension", () => {
    expect(fileCategory("resultado.xlsx", "application/octet-stream")).toBe(
      FileCategory.SPREADSHEET
    );
    expect(fileCategory("lote.zip", "binary/octet-stream")).toBe(
      FileCategory.ARCHIVE
    );
  });

  test("text/plain does not turn a csv into a document", () => {
    // Servers hand back text/plain for csv, md and tsv alike, so it is treated
    // as uninformative and the extension decides.
    expect(fileCategory("resultado.csv", "text/plain")).toBe(
      FileCategory.SPREADSHEET
    );
  });

  test("a missing MIME type is fine", () => {
    expect(fileCategory("resultado.xlsx")).toBe(FileCategory.SPREADSHEET);
    expect(fileCategory("resultado.xlsx", null)).toBe(FileCategory.SPREADSHEET);
    expect(fileCategory("resultado.xlsx", "")).toBe(FileCategory.SPREADSHEET);
  });

  test("a meaningful MIME type wins over a misleading extension", () => {
    expect(fileCategory("relatorio.txt", "application/pdf")).toBe(
      FileCategory.DOCUMENT
    );
  });
});

describe("fileCategory casing", () => {
  test("an uppercase extension resolves", () => {
    expect(fileCategory("RESULTADO.XLSX")).toBe(FileCategory.SPREADSHEET);
    expect(fileCategory("CAPTURA.PNG")).toBe(FileCategory.IMAGE);
  });

  test("the category does not depend on filename casing", () => {
    const names = [
      "Resultado Vale Norte.XlSx",
      "resultado vale norte.xlsx",
      "RESULTADO VALE NORTE.XLSX",
    ];
    const categories = new Set(names.map((name) => fileCategory(name)));
    expect(categories).toEqual(new Set([FileCategory.SPREADSHEET]));
  });

  test("an uppercase MIME type resolves", () => {
    expect(fileCategory("contrato", "APPLICATION/PDF")).toBe(
      FileCategory.DOCUMENT
    );
  });
});

describe("fileCategory fallback", () => {
  test("an unknown format is OTHER, not DOCUMENT", () => {
    expect(fileCategory("dados.bin", "application/octet-stream")).toBe(
      FileCategory.OTHER
    );
    expect(fileCategory("firmware.xyz")).toBe(FileCategory.OTHER);
  });

  test("a file with no extension at all is OTHER", () => {
    expect(fileCategory("LEIAME")).toBe(FileCategory.OTHER);
    expect(fileCategory("")).toBe(FileCategory.OTHER);
    expect(fileCategory(null)).toBe(FileCategory.OTHER);
    expect(fileCategory(undefined)).toBe(FileCategory.OTHER);
  });

  test("a trailing dot is not an extension", () => {
    expect(fileCategory("relatorio.")).toBe(FileCategory.OTHER);
  });

  test("a dotfile is not classified by its name", () => {
    expect(fileCategory(".gitignore")).toBe(FileCategory.OTHER);
  });
});

describe("category identity", () => {
  test("every category has a distinct glyph, so identity never needs colour", () => {
    const categories = Object.values(FileCategory);
    const glyphs = new Set(categories.map((c) => fileCategoryIcon(c)));

    expect(categories).toHaveLength(8);
    expect(glyphs.size).toBe(8);
  });

  test("every category has a catalog label key", () => {
    for (const category of Object.values(FileCategory)) {
      expect(FILE_CATEGORY_LABEL_KEYS[category]).toMatch(/^[a-z]+$/);
    }
  });

  test("agrees with isImageFile, which seeds it", () => {
    for (const name of [
      "a.png",
      "a.jpg",
      "a.jpeg",
      "a.gif",
      "a.webp",
      "a.svg",
      "a.bmp",
    ]) {
      expect(isImageFile(name)).toBe(true);
      expect(fileCategory(name)).toBe(FileCategory.IMAGE);
    }
    expect(isImageFile("a.xlsx")).toBe(false);
    expect(fileCategory("a.xlsx")).not.toBe(FileCategory.IMAGE);
  });
});
