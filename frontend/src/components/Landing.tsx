import { useState } from "react";
import { createRoom } from "../api";

interface LandingProps {
  onRoomReady: (code: string) => void;
}

export function Landing({ onRoomReady }: LandingProps) {
  const [joinCode, setJoinCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    setError(null);
    setCreating(true);
    try {
      const code = await createRoom();
      onRoomReady(code);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't create a room.");
    } finally {
      setCreating(false);
    }
  };

  const handleJoin = () => {
    const code = joinCode.trim().toUpperCase();
    if (code) onRoomReady(code);
  };

  return (
    <div className="landing">
      <h1>Bid Euchre</h1>

      <div className="landing-panel">
        <button type="button" onClick={handleCreate} disabled={creating}>
          Create room
        </button>
      </div>

      <div className="landing-panel">
        <input
          type="text"
          placeholder="Room code"
          value={joinCode}
          onChange={(e) => setJoinCode(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleJoin()}
          maxLength={6}
        />
        <button type="button" onClick={handleJoin} disabled={!joinCode.trim()}>
          Join room
        </button>
      </div>

      {error && <p className="landing-error">{error}</p>}
    </div>
  );
}
