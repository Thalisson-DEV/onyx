import type { IconProps } from "@opal/types";

// TON: the product mark is the Vale Norte symbol, served from /public/ton.
// Every inherited surface that showed the upstream mark (provider dialogs,
// connection icons) now shows it.
const SvgOnyxLogo = ({ size, ...props }: IconProps) => (
  <svg
    height={size}
    width={size}
    viewBox="0 0 64 64"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    {...props}
  >
    <image href="/ton/favicon.png" width="64" height="64" />
  </svg>
);
export default SvgOnyxLogo;
