from __future__ import annotations

import json
import logging

import redis.asyncio as aioredis
from mcp.server.streamable_http import EventCallback, EventMessage, EventStore
from mcp.types import JSONRPCMessage
from app.utils.redis import get_redis_client


EventId = str
StreamId = str
SEP = "|"  # separator for composite event ids: "<stream_id>|<redis_id>"


logger = logging.getLogger(__name__)


class RedisEventStore(EventStore):
    """
    Redis-backed EventStore for FastMCP Streamable HTTP.

    - One Redis Stream per 'stream_id': key = "{ns}:stream:{stream_id}"
      Each entry: field 'e' = JSON of the JSON-RPC message (dict).
    - Reverse lookup (optional/caching): "{ns}:event:{event_id}" -> stream_id
      (We still encode stream_id in event_id to avoid cross-stream id collisions.)

    Memory/retention:
      * Streams trimmed with MAXLEN (approximate) to cap memory.
      * TTL on streams and event-lookup keys keeps old sessions from lingering.
    """

    def __init__(
        self,
        *,
        namespace: str = "mcp",
        ttl_seconds: int = 24 * 60 * 60,
        max_events_per_stream: int = 2000,
    ) -> None:
        self.r: aioredis.Redis = get_redis_client()
        self.ns = namespace
        self.ttl = int(ttl_seconds)
        self.maxlen = int(max_events_per_stream)

    # --------------- key helpers ---------------

    def _k_stream(self, stream_id: StreamId) -> str:
        return f"{self.ns}:stream:{stream_id}"

    def _k_event_lookup(self, event_id: EventId) -> str:
        return f"{self.ns}:event:{event_id}"

    # --------------- EventStore API ---------------

    async def store_event(
        self,
        stream_id: StreamId,
        message: JSONRPCMessage,
    ) -> EventId:
        """
        Append a message to the stream and return a globally-unique EventId.
        EventId format: "<stream_id>|<redis_stream_id>"
        """
        # Normalize to dict and compact JSON
        if hasattr(message, "model_dump"):
            payload = message.model_dump()
        elif isinstance(message, dict):
            payload = message
        else:
            # last resort: try to coerce
            payload = json.loads(json.dumps(message, default=str))

        data = {"e": json.dumps(payload, separators=(",", ":"), ensure_ascii=False)}
        stream_key = self._k_stream(stream_id)

        redis_id: str = await self.r.xadd(
            stream_key,
            data,
            maxlen=self.maxlen,
            approximate=True,  # ~MAXLEN for performance
        )
        event_id: str = f"{stream_id}{SEP}{redis_id}"

        # Cache reverse lookup (not strictly necessary now, but keeps TTL mgmt simple)
        pipe = self.r.pipeline()
        pipe.set(self._k_event_lookup(event_id), stream_id, ex=self.ttl)
        pipe.expire(stream_key, self.ttl)
        await pipe.execute()

        return event_id

    async def replay_events_after(
        self,
        last_event_id: EventId,
        send_callback: EventCallback,
    ) -> StreamId | None:
        """
        Replay all events STRICTLY AFTER `last_event_id` to the provided callback.
        Returns the stream_id if it could be resolved, else None.
        """
        if not last_event_id:
            return None

        # Prefer parsing from composite id; fallback to cached lookup for backward compat
        stream_id: str | None = None
        redis_id: str | None = None
        if SEP in last_event_id:
            stream_id, redis_id = last_event_id.split(SEP, 1)
        else:
            stream_id = await self.r.get(self._k_event_lookup(last_event_id))
            redis_id = last_event_id  # assume caller gave us the raw redis id

        if not stream_id or not redis_id:
            return None

        stream_key = self._k_stream(stream_id)

        # XRANGE from (redis_id) to "+" to skip the last seen event
        entries = await self.r.xrange(stream_key, min=f"({redis_id})", max="+")

        if not entries:
            # keep the stream warm
            await self.r.expire(stream_key, self.ttl)
            return stream_id

        pipe = self.r.pipeline()
        for rid, fields in entries:
            raw = fields.get("e")
            if raw is None:
                continue
            try:
                msg_dict = json.loads(raw)
                message = JSONRPCMessage.model_validate(msg_dict)
                await send_callback(EventMessage(message=message, event_id=f"{stream_id}{SEP}{rid}"))
            except Exception:
                logger.warning("Could not parse event %s data: %r", rid, raw, exc_info=True)
                continue

            # Extend TTL for this event-id mapping (optional)
            pipe.expire(self._k_event_lookup(f"{stream_id}{SEP}{rid}"), self.ttl)

        # Refresh stream TTL after replay
        pipe.expire(stream_key, self.ttl)
        await pipe.execute()

        return stream_id
