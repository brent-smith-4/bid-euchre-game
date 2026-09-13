import "./App.css";
import { GameRoom } from "./components/GameRoom";
import { Landing } from "./components/Landing";
import { useRoute } from "./useRoute";

function App() {
  const { roomCode, goToRoom } = useRoute();

  if (roomCode === null) {
    return <Landing onRoomReady={goToRoom} />;
  }

  return <GameRoom roomCode={roomCode} />;
}

export default App;
