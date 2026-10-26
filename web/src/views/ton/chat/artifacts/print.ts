import type { TonArtifact } from "@/lib/ton/artifacts";

/**
 * Prints the open artifact through the browser, which saves it as PDF. The
 * stylesheet hides everything but `.tn-art-print`; a deck prints landscape,
 * one slide per page. The panel renders first, so this waits two frames.
 */
export function printArtifact(artifact: TonArtifact): void {
  const style = document.createElement("style");
  style.textContent =
    artifact.artifact_kind === "apresentacao"
      ? "@page { size: A4 landscape; margin: 10mm; }"
      : "@page { size: A4 portrait; margin: 14mm; }";
  const title = document.title;
  requestAnimationFrame(() =>
    requestAnimationFrame(() => {
      document.head.appendChild(style);
      document.documentElement.classList.add("tn-printing-artifact");
      document.title = artifact.title;
      const cleanup = () => {
        style.remove();
        document.documentElement.classList.remove("tn-printing-artifact");
        document.title = title;
        window.removeEventListener("afterprint", cleanup);
      };
      window.addEventListener("afterprint", cleanup);
      window.print();
    })
  );
}
