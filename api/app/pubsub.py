"""Pub/Sub-style trigger seam.

Local dev uses an in-process publisher so a "new activity detected" event kicks off
a run without external infra. In production, swap `LocalPublisher` for a Cloud
Pub/Sub publisher and run the run-engine as a push-subscription handler — the
autonomy story ("event wakes the agent") is identical.
"""
import asyncio

class LocalPublisher:
    def __init__(self):
        self._handlers = {}

    def subscribe(self, topic, handler):
        self._handlers[topic] = handler

    async def publish(self, topic, data):
        handler = self._handlers.get(topic)
        if handler is None:
            return None
        return await handler(data)

# --- Production seam (google-cloud-pubsub) ---
# from google.cloud import pubsub_v1
# publisher = pubsub_v1.PublisherClient()
# publisher.publish(topic_path, json.dumps(data).encode())
# ...and deploy the run engine behind a push subscription endpoint.

bus = LocalPublisher()
TOPIC_ACTIVITY = "activity.detected"
