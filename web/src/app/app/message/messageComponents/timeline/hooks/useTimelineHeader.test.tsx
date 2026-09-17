import { render, screen } from "@tests/setup/test-utils";

import { PacketType, type Packet } from "@/app/app/services/streamingModels";
import { useTimelineHeader } from "@/app/app/message/messageComponents/timeline/hooks/useTimelineHeader";
import type { TurnGroup } from "@/app/app/message/messageComponents/timeline/transformers";

function packet(
  type: PacketType,
  fields: Record<string, unknown> = {}
): Packet {
  return {
    placement: { turn_index: 0, tab_index: 0 },
    obj: { type, ...fields },
  } as Packet;
}

function group(firstPacket: Packet): TurnGroup[] {
  return [
    {
      turnIndex: 0,
      isParallel: false,
      steps: [
        {
          key: "0-0",
          turnIndex: 0,
          tabIndex: 0,
          packets: [firstPacket],
        },
      ],
    },
  ];
}

function Header({ groups }: { groups: TurnGroup[] }) {
  const { headerText } = useTimelineHeader(groups);
  return <p>{headerText}</p>;
}

describe("safe operational activity mapping", () => {
  test.each([
    [PacketType.FETCH_TOOL_START, {}, "Opening links…"],
    [PacketType.PYTHON_TOOL_START, {}, "Running code…"],
    [PacketType.FILE_READER_START, {}, "Reading file…"],
    [PacketType.REASONING_START, {}, "Processing…"],
    [PacketType.CUSTOM_TOOL_START, { tool_name: "Ledger" }, "Running Ledger…"],
  ])("maps %s to a packet-backed label", (type, fields, label) => {
    render(<Header groups={group(packet(type, fields))} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  test("uses only a generic state for an unsupported packet", () => {
    render(<Header groups={group(packet(PacketType.MESSAGE_START))} />);
    expect(screen.getByText("Processing…")).toBeInTheDocument();
    expect(screen.queryByText(/contract|rule|source|search/i)).toBeNull();
  });
});
