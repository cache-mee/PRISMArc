const SESSION_ID_STORAGE_KEY = "salon-chat-session-id";

export function getOrCreateSessionId(): string {
  const existingSessionId = sessionStorage.getItem(SESSION_ID_STORAGE_KEY);
  if (existingSessionId) {
    return existingSessionId;
  }

  const newSessionId = crypto.randomUUID();
  sessionStorage.setItem(SESSION_ID_STORAGE_KEY, newSessionId);
  return newSessionId;
}
