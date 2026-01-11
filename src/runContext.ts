import Phaser from 'phaser';
import { worldWindow } from './worldWindow';
import { UXTracker } from './observability/uxTracker';
import { EventSink } from './observability/eventSink';

function uuidv4(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export class RunContext {
  public sessionId: string;
  public uxTracker: UXTracker;
  public worldWindow = worldWindow;
  public game?: Phaser.Game;

  // Constructor accepts a sink and optional sessionId. If sessionId is not provided,
  // it is generated per-load here. UXTracker is created inside the context.
  constructor(sink: EventSink, sessionId?: string, debounceMs = 300) {
    this.sessionId = sessionId ?? uuidv4();
    this.uxTracker = new UXTracker(sink, this.sessionId, debounceMs);
  }
}
