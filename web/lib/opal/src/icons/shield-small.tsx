import type { IconProps } from "@opal/types";
const SvgShieldSmall = ({ size, ...props }: IconProps) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 16 16"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    stroke="currentColor"
    {...props}
  >
    <path
      d="M8 4.75L10.75 5.75V8C10.75 9.55 9.55 10.75 8 11.25C6.45 10.75 5.25 9.55 5.25 8V5.75L8 4.75Z"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);
export default SvgShieldSmall;
