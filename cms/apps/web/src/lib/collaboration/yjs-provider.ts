/**
 * WebSocket provider factory for Yjs collaboration.
 * Connects to a WebSocket server for real-time document sync.
 */
import * as Y from "yjs";
import { WebsocketProvider } from "y-websocket";

const WS_URL = process.env.NEXT_PUBLIC_COLLAB_WS_URL ?? "ws://localhost:1234";

export function createWebSocketProvider(
  roomName: string,
  doc: Y.Doc,
): WebsocketProvider {
  return new WebsocketProvider(WS_URL, roomName, doc, {
    connect: true,
    maxBackoffTime: 10000,
  });
}
