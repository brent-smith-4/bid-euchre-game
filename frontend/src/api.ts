import { HTTP_BASE } from "./config";

export async function createRoom(): Promise<string> {
  const response = await fetch(`${HTTP_BASE}/rooms`, { method: "POST" });
  if (!response.ok) {
    if (response.status === 429) {
      throw new Error("Too many rooms created from this connection - try again in a minute.");
    }
    throw new Error("Couldn't create a room right now.");
  }
  const data = (await response.json()) as { room_code: string };
  return data.room_code;
}
