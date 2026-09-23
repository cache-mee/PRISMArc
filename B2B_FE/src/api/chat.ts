export interface ChatRequest {
  session_id: string;
  message?: string | null;
}

export interface ChatResponse {
  reply: string;
}

export const DEFAULT_CHAT_ERROR_MESSAGE =
  "Failed to process your request. Please try again later.";

/** Thrown for a non-OK /chat response, carrying a user-displayable message. */
export class ChatRequestError extends Error {}

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
    throw new ChatRequestError(await extractErrorMessage(response));
  }

  return (await response.json()) as ChatResponse;
}

async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? (body as { detail: unknown }).detail
        : undefined;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  } catch {
    // Response body wasn't JSON (e.g. an upstream gateway error page) —
    // fall through to the generic message below.
  }
  return DEFAULT_CHAT_ERROR_MESSAGE;
}
