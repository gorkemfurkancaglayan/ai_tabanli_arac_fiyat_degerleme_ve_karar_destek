import { io } from 'socket.io-client';

// Flask sunucumuzun adresi. autoConnect: false ile bağlantıyı manuel kontrol edeceğiz.
const socket = io('http://127.0.0.1:5000', {
  autoConnect: false,
});

export default socket;