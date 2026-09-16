import { useState } from "react";
import { createRoom } from "../api";
import { Modal } from "./Modal";
import { RulesContent } from "./RulesContent";

interface LandingProps {
  onRoomReady: (code: string) => void;
}

export function Landing({ onRoomReady }: LandingProps) {
  const [joinCode, setJoinCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [showRules, setShowRules] = useState(false);

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
      <div className="landing-hero">
        <span className="landing-suits" aria-hidden="true">
          &spades; &hearts; &diams; &clubs;
        </span>
        <h1 className="landing-title">Bid Euchre</h1>
        <p className="landing-tagline">A real-time, server-authoritative table for four.</p>
      </div>

      <div className="landing-table">
        <div className="landing-panel">
          <button type="button" className="felt-button" onClick={handleCreate} disabled={creating}>
            Create room
          </button>
        </div>

        <div className="landing-divider">or</div>

        <div className="landing-panel">
          <input
            type="text"
            placeholder="Room code"
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleJoin()}
            maxLength={6}
          />
          <button type="button" className="felt-button" onClick={handleJoin} disabled={!joinCode.trim()}>
            Join room
          </button>
        </div>

        {error && <p className="landing-error">{error}</p>}
      </div>

      <button type="button" className="how-to-play-button" onClick={() => setShowRules(true)}>
        How to play
      </button>

      {showRules && (
        <Modal title="How to play Bid Euchre" onClose={() => setShowRules(false)}>
          <RulesContent />
        </Modal>
      )}
    </div>
  );
}
