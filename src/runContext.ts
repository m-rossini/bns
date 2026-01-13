import Phaser from 'phaser';
import { UXTracker } from './observability/uxTracker';
import { SimulationTracker } from './observability/simulationTracker';
import { EventSink, Tracker } from './observability/types';
import { uuidv4 } from './utils/uuid';

export class RunContext {
  public sessionId: string;
  private trackers: Tracker[] = [];
  public game?: Phaser.Game;

  // Constructor accepts a sink and optional sessionId. If sessionId is not provided,
  // it is generated per-load here. Trackers are created inside the context.
  constructor(sink: EventSink, sessionId?: string, debounceMs = 300) {
    this.sessionId = sessionId ?? uuidv4();
    this.trackers.push(new UXTracker(sink, this.sessionId, debounceMs));
    this.trackers.push(new SimulationTracker(sink, this.sessionId, 1000)); // Sample every 1s
  }

  public getTracker<T extends Tracker>(type: new (...args: any[]) => T): T {
    const tracker = this.trackers.find(t => t instanceof type);
    if (!tracker) {
      throw new Error(`Tracker of type ${type.name} not found in RunContext`);
    }
    return tracker as T;
  }
}
