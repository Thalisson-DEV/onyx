import type { IconProps } from "@opal/types";
const SvgCartSmall = ({ size, ...props }: IconProps) => (
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
      d="M4.5 4.75H5.5L6.5 9.25H10.25L11.25 6.25H5.85"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <circle cx={7} cy={11} r={0.5} strokeWidth={1.25} />
    <circle cx={9.75} cy={11} r={0.5} strokeWidth={1.25} />
  </svg>
);
export default SvgCartSmall;
