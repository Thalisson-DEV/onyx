import { render, screen } from "@tests/setup/test-utils";

import {
  PacketType,
  type Packet,
  type ReasoningPacket,
} from "@/app/app/services/streamingModels";
import {
  RenderType,
  type RendererOutput,
} from "@/app/app/message/messageComponents/interfaces";
import ReasoningRenderer from "@/app/app/message/messageComponents/timeline/renderers/reasoning/ReasoningRenderer";
import type { MinimalAgent } from "@/lib/agents/types";

const SECRET = "private model reasoning must never render";
const AGENT: MinimalAgent = {
  id: 1,
  name: "Test agent",
  description: "",
  tools: [],
  starter_messages: null,
  document_sets: [],
  is_public: false,
  is_listed: false,
  display_priority: null,
  is_featured: false,
  builtin_persona: false,
  owner: null,
  owner_group: null,
  user_permission: null,
};

function packet(
  type: PacketType,
  fields: Record<string, unknown> = {}
): Packet {
  return {
    placement: { turn_index: 0, tab_index: 0 },
    obj: { type, ...fields },
  } as Packet;
}

function Results({ results }: { results: RendererOutput }) {
  return (
    <div>
      {results.map((result, index) => (
        <div key={index}>
          {result.status}
          {result.content}
        </div>
      ))}
    </div>
  );
}

function renderPackets(packets: Packet[]) {
  return render(
    <ReasoningRenderer
      packets={packets as ReasoningPacket[]}
      state={{ agent: AGENT }}
      onComplete={jest.fn()}
      renderType={RenderType.FULL}
      animate={false}
      stopPacketSeen={false}
    >
      {(results) => <Results results={results} />}
    </ReasoningRenderer>
  );
}

describe("private reasoning", () => {
  test.each([
    ["one delta", [packet(PacketType.REASONING_DELTA, { reasoning: SECRET })]],
    [
      "multiple deltas",
      [
        packet(PacketType.REASONING_DELTA, { reasoning: SECRET }),
        packet(PacketType.REASONING_DELTA, { reasoning: "second secret" }),
      ],
    ],
    [
      "an answer packet",
      [
        packet(PacketType.REASONING_DELTA, { reasoning: SECRET }),
        packet(PacketType.MESSAGE_DELTA, { content: "Public answer" }),
      ],
    ],
    [
      "a tool packet",
      [
        packet(PacketType.REASONING_DELTA, { reasoning: SECRET }),
        packet(PacketType.CUSTOM_TOOL_START, { tool_name: "Ledger" }),
      ],
    ],
    [
      "an error packet",
      [
        packet(PacketType.REASONING_DELTA, { reasoning: SECRET }),
        packet(PacketType.ERROR, { message: "Public failure" }),
      ],
    ],
  ])("does not expose deltas with %s", (_, packets) => {
    const { container } = renderPackets(packets);

    expect(container).not.toHaveTextContent(SECRET);
    expect(container).not.toHaveTextContent("second secret");
    expect(screen.queryByRole("button", { name: /copy|download/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /download/i })).toBeNull();
  });

  test("reports running, completed, and failed packet states", () => {
    const running = renderPackets([packet(PacketType.REASONING_START)]);
    expect(
      running.container.querySelector('[data-activity-state="running"]')
    ).toBeTruthy();
    running.unmount();

    const completed = renderPackets([
      packet(PacketType.REASONING_START),
      packet(PacketType.SECTION_END),
    ]);
    expect(
      completed.container.querySelector('[data-activity-state="completed"]')
    ).toBeTruthy();
    completed.unmount();

    const failed = renderPackets([
      packet(PacketType.REASONING_START),
      packet(PacketType.ERROR, { message: "Public failure" }),
    ]);
    expect(
      failed.container.querySelector('[data-activity-state="failed"]')
    ).toBeTruthy();
    expect(failed.container).toHaveTextContent("Execution failed");
  });
});
