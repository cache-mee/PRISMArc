export interface ChatRequest {
  session_id: string;
  message?: string | null;
}

export interface ChatResponse {
  reply: string;
}

export async function sendChatMessage(
  request: ChatRequest,
): Promise<ChatResponse> {
  const response = await fetch("/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(
      `Chat request failed with status ${response.status.toString()}`,
    );
  }

  return (await response.json()) as ChatResponse;
}
