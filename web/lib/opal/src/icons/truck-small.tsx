import type { IconProps } from "@opal/types";
const SvgTruckSmall = ({ size, ...props }: IconProps) => (
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
      d="M8.75 9.75V5.25H4.75V9.75H5.25M8.75 7.25H10.5L11.25 8.5V9.75H10.75M8.75 9.75H7.25"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <circle cx={6.25} cy={10} r={1} strokeWidth={1.5} />
    <circle cx={9.75} cy={10} r={1} strokeWidth={1.5} />
  </svg>
);
export default SvgTruckSmall;
