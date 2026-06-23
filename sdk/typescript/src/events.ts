/** Event handler for webhook events */
export type EventType =
  | 'context.created' | 'context.updated' | 'context.deleted'
  | 'context.status_changed' | 'context.confidence_changed'
  | 'relation.created' | 'relation.deleted'
  | 'entity.created' | 'entity.updated';

type EventHandlerFn = (payload: unknown) => void;

export class EventHandler {
  private secret: string;
  private handlers: Map<EventType, EventHandlerFn[]> = new Map();

  constructor(webhookSecret: string) {
    this.secret = webhookSecret;
  }

  on(eventType: EventType, handler: EventHandlerFn): void {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, []);
    }
    this.handlers.get(eventType)!.push(handler);
  }

  async verifySignature(payload: string, signature: string): Promise<boolean> {
    const encoder = new TextEncoder();
    const key = await crypto.subtle.importKey(
      'raw', encoder.encode(this.secret.slice(0, 32)),
      { name: 'HMAC', hash: 'SHA-256' }, false, ['verify']
    );
    const sigBytes = new Uint8Array(signature.match(/.{2}/g)!.map(b => parseInt(b, 16)));
    return crypto.subtle.verify(
      'HMAC', key, sigBytes, encoder.encode(payload)
    );
  }

  handleEvent(eventType: EventType, payload: unknown): void {
    const handlers = this.handlers.get(eventType) || [];
    handlers.forEach(h => { try { h(payload); } catch {} });
  }
}
