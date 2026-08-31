let cachedPublisher = null;

export function createPlatformEventPublisher({
  projectId = process.env.GOOGLE_CLOUD_PROJECT,
  topic = process.env.MOCKDROP_PUBSUB_TOPIC,
  enabled = process.env.MOCKDROP_PUBSUB_ENABLED === "true"
} = {}) {
  if (!enabled || !topic) {
    return {
      enabled: false,
      topic,
      async publish() {
        return null;
      }
    };
  }

  return {
    enabled: true,
    topic,
    async publish(event) {
      if (!cachedPublisher) {
        const { PubSub } = await import("@google-cloud/pubsub");
        cachedPublisher = new PubSub({ projectId }).topic(topic);
      }

      const messageId = await cachedPublisher.publishMessage({
        data: Buffer.from(JSON.stringify(event)),
        orderingKey: event.appealId || event.caseId || "mockdrop",
        attributes: {
          type: event.type || "PLATFORM_EVENT",
          externalEventId: event.externalEventId || ""
        }
      });

      return messageId;
    }
  };
}
