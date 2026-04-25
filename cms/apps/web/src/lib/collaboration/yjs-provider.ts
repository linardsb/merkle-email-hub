/**
 * Hub-authenticated WebSocket provider for Yjs collaboration.
 * Connects to the Hub backend's /ws/collab/{roomId} endpoint with JWT auth.
 */
import * as Y from "yjs";
import { WebsocketProvider } from "y-websocket";

const WS_BASE_URL = process.env.NEXT_PUBLIC_COLLAB_WS_URL ?? "ws://localhost:8891";

export interface HubProviderOptions {
  /** JWT access token for authentication */
  token: string;
  /** Auto-connect on creation (default: true) */
  connect?: boolean;
  /** Max backoff time in ms for reconnection (default: 30000) */
  maxBackoffTime?: number;
}

/**
 * Creates a Hub-authenticated WebSocket provider for a collaboration room.
 *
 * The provider handles:
 * - JWT authentication via ?token= query parameter
 * - Automatic reconnection with exponential backoff
 * - Yjs sync protocol (SyncStep1/Step2/Update)
 * - Awareness protocol for cursor/presence sharing
 */
export function createHubProvider(
  roomId: string,
  doc: Y.Doc,
  options: HubProviderOptions,
): WebsocketProvider {
  const { token, connect = true, maxBackoffTime = 30_000 } = options;

  // y-websocket appends roomName to the URL path, but our backend uses
  // /ws/collab/{room_id} with ?token= auth. We build the full URL with
  // params and pass an empty string as roomName to avoid double path segments.
  const wsUrl = `${WS_BASE_URL}/ws/collab/${encodeURIComponent(roomId)}`;

  const provider = new WebsocketProvider(wsUrl, "", doc, {
    connect,
    maxBackoffTime,
    params: { token },
  });

  return provider;
}

/** Connection status for UI indicators */
export type ConnectionStatus = "connecting" | "connected" | "disconnected";

/**
 * Subscribe to provider connection status changes.
 * Returns an unsubscribe function.
 */
export function onConnectionStatus(
  provider: WebsocketProvider,
  callback: (status: ConnectionStatus) => void,
): () => void {
  const handler = ({ status }: { status: string }) => {
    callback(status as ConnectionStatus);
  };
  provider.on("status", handler);
  return () => provider.off("status", handler);
}
