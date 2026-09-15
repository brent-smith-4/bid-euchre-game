import "./App.css";
import { GameRoom } from "./components/GameRoom";
import { Landing } from "./components/Landing";
import { useRoute } from "./useRoute";

function App() {
  const { roomCode, goToRoom, goHome } = useRoute();

  if (roomCode === null) {
    return <Landing onRoomReady={goToRoom} />;
  }

  return <GameRoom roomCode={roomCode} onGoHome={goHome} />;
}

export default App;
