import { StrictMode } from "react";
import { render, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import ChatWindow from "../src/chat/ChatWindow";
import * as chatApi from "../src/api/chat";

describe("ChatWindow", () => {
  it("sends the opening greeting request only once under StrictMode's double-invoked effects", async () => {
    const sendChatMessageSpy = vi
      .spyOn(chatApi, "sendChatMessage")
      .mockResolvedValue({
        reply: "Could I get your phone number to pull up your account?",
      });

    render(
      <StrictMode>
        <ChatWindow />
      </StrictMode>,
    );

    await waitFor(() => {
      expect(sendChatMessageSpy).toHaveBeenCalled();
    });

    expect(sendChatMessageSpy).toHaveBeenCalledTimes(1);
  });
});
