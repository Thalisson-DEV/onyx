import type { IconProps } from "@opal/types";
const SvgUsersSmall = ({ size, ...props }: IconProps) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 16 16"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    stroke="currentColor"
    {...props}
  >
    <circle cx={7} cy={6.25} r={1.5} strokeWidth={1.5} />
    <path
      d="M4.5 11.25C4.5 9.87 5.62 8.75 7 8.75C8.38 8.75 9.5 9.87 9.5 11.25M9.75 4.95C10.4 5.15 10.85 5.75 10.85 6.45C10.85 7.15 10.4 7.75 9.75 7.95M10.75 9C11.2 9.4 11.5 10.05 11.5 11"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);
export default SvgUsersSmall;
