import { useCallback, useEffect, useState } from "react";

const ROOM_PATH = /^\/room\/([^/]+)$/;

function parseRoomCode(pathname: string): string | null {
  const match = ROOM_PATH.exec(pathname);
  return match ? match[1] : null;
}

export interface Route {
  roomCode: string | null;
  goToRoom: (code: string) => void;
}

// Two "pages" (landing, room) don't justify pulling in a router library -
// a few lines of manual pushState/popstate handling covers it.
export function useRoute(): Route {
  const [roomCode, setRoomCode] = useState(() => parseRoomCode(window.location.pathname));

  useEffect(() => {
    const onPopState = () => setRoomCode(parseRoomCode(window.location.pathname));
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const goToRoom = useCallback((code: string) => {
    window.history.pushState(null, "", `/room/${code}`);
    setRoomCode(code);
  }, []);

  return { roomCode, goToRoom };
}
