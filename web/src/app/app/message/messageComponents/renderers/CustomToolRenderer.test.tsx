import { render } from "@tests/setup/test-utils";

import {
  PacketType,
  type CustomToolPacket,
  type Packet,
} from "@/app/app/services/streamingModels";
import {
  RenderType,
  type RendererOutput,
} from "@/app/app/message/messageComponents/interfaces";
import CustomToolRenderer from "@/app/app/message/messageComponents/renderers/CustomToolRenderer";

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

function renderTool(packets: Packet[]) {
  return render(
    <CustomToolRenderer
      packets={packets as CustomToolPacket[]}
      state={{}}
      onComplete={jest.fn()}
      renderType={RenderType.FULL}
      animate={false}
      stopPacketSeen={false}
    >
      {(results) => <Results results={results} />}
    </CustomToolRenderer>
  );
}

describe("custom tool activity", () => {
  const start = packet(PacketType.CUSTOM_TOOL_START, { tool_name: "Ledger" });

  test("reports the running state", () => {
    const { container } = renderTool([start]);
    expect(
      container.querySelector('[data-activity-state="running"]')
    ).toBeTruthy();
    expect(container).toHaveTextContent("Ledger running");
  });

  test("reports the completed state", () => {
    const { container } = renderTool([start, packet(PacketType.SECTION_END)]);
    expect(
      container.querySelector('[data-activity-state="completed"]')
    ).toBeTruthy();
    expect(container).toHaveTextContent("Ledger completed");
  });

  test("reports an ERROR packet as failed", () => {
    const { container } = renderTool([
      start,
      packet(PacketType.ERROR, { message: "Connection failed" }),
    ]);
    expect(
      container.querySelector('[data-activity-state="failed"]')
    ).toBeTruthy();
    expect(container).toHaveTextContent("Ledger failed");
    expect(container).toHaveTextContent("Connection failed");
  });
});
