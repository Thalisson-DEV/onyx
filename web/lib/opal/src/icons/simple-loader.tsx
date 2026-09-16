import type { IconProps } from "@opal/types";
import { cn } from "@opal/utils";
import SvgLoader from "@opal/icons/loader";

// `motion-safe:` matches IconLoader and OnyxLoader: under
// `prefers-reduced-motion: reduce` the glyph stays, the rotation stops.
const SvgSimpleLoader = ({ className, ...props }: IconProps) => (
  <SvgLoader
    className={cn("h-4 w-4 motion-safe:animate-spin", className)}
    {...props}
  />
);

export default SvgSimpleLoader;
