"""Pydantic schemas for WebSocket streaming protocol.

These define the bidirectional message protocol:
- Client -> Server: subscribe/unsubscribe with optional filters
- Server -> Client: data updates, errors, acknowledgements
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class WsSubscribeMessage(BaseModel):
    """Client request to subscribe to data updates.

    Attributes:
        action: Must be "subscribe".
        filters: Optional key-value filters to narrow the stream.
            Keys and values are domain-specific (e.g., {"route_id": "22", "feed_id": "riga"}).
            Omitted keys mean "all values" for that dimension.
    """

    model_config = ConfigDict(strict=True)

    action: Literal["subscribe"]
    filters: dict[str, str] | None = None


class WsUnsubscribeMessage(BaseModel):
    """Client request to unsubscribe from updates.

    Attributes:
        action: Must be "unsubscribe".
    """

    model_config = ConfigDict(strict=True)

    action: Literal["unsubscribe"]


class WsDataUpdate(BaseModel):
    """Server push of real-time data.

    Attributes:
        type: Message type discriminator.
        topic: The data topic/channel this update belongs to.
        count: Number of items in this update.
        items: List of data item dicts (shape is domain-specific).
        timestamp: ISO 8601 server time when update was assembled.
    """

    model_config = ConfigDict(strict=True)

    type: Literal["data_update"] = "data_update"
    topic: str
    count: int
    items: list[dict[str, object]]
    timestamp: str


class WsError(BaseModel):
    """Server error message sent to client.

    Attributes:
        type: Message type discriminator.
        code: Machine-readable error code.
        message: Human-readable error description.
    """

    model_config = ConfigDict(strict=True)

    type: Literal["error"] = "error"
    code: str
    message: str


class WsAck(BaseModel):
    """Server acknowledgement of client action.

    Attributes:
        type: Message type discriminator.
        action: Which client action was acknowledged.
        filters: Currently active filters after the action.
    """

    model_config = ConfigDict(strict=True)

    type: Literal["ack"] = "ack"
    action: Literal["connected", "subscribe", "unsubscribe"]
    filters: dict[str, str | None]
