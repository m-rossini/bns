import Phaser from 'phaser';
import { worldWindow } from './worldWindow';
import { UXTracker } from './observability/uxTracker';
import { EventSink, Tracker } from './observability/types';
import { uuidv4 } from './utils/uuid';

export class RunContext {
  public sessionId: string;
  private trackers: Tracker[] = [];
  public worldWindow = worldWindow;
  public game?: Phaser.Game;

  // Constructor accepts a sink and optional sessionId. If sessionId is not provided,
  // it is generated per-load here. UXTracker is created inside the context.
  constructor(sink: EventSink, sessionId?: string, debounceMs = 300) {
    this.sessionId = sessionId ?? uuidv4();
    this.trackers.push(new UXTracker(sink, this.sessionId, debounceMs));
  }

  public getTracker<T extends Tracker>(type: new (...args: any[]) => T): T {
    const tracker = this.trackers.find(t => t instanceof type);
    if (!tracker) {
      throw new Error(`Tracker of type ${type.name} not found in RunContext`);
    }
    return tracker as T;
  }
}
