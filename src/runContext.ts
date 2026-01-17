import Phaser from 'phaser';
import { UXTracker } from './observability/uxTracker';
import { SimulationTracker } from './observability/simulationTracker';
import { Tracker, EventType } from './observability/types';
import { EventSinkMap } from './observability/eventSinkFactory';
import { uuidv4 } from './utils/uuid';

export class RunContext {
  public sessionId: string;
  private trackers: Tracker[];
  public game?: Phaser.Game;

  // Constructor accepts trackers and optional sessionId.
  // Use RunContext.createTrackers() to instantiate trackers without changing caller code.
  constructor(trackers: Tracker[], sessionId?: string) {
    this.sessionId = sessionId ?? uuidv4();
    this.trackers = trackers;
  }

  /**
   * Static factory method to instantiate all trackers.
   * Each tracker uses the appropriate sink for its event type.
   */
  public static createTrackers(sinks: EventSinkMap, sessionId: string, debounceMs = 300): Tracker[] {
    const uxSink = sinks[EventType.UX_ACTION];
    const simSink = sinks[EventType.SIMULATION_EVENT];

    if (!uxSink) {
      throw new Error('UX_ACTION sink is required');
    }
    if (!simSink) {
      throw new Error('SIMULATION_EVENT sink is required');
    }

    return [
      new UXTracker(uxSink, sessionId, debounceMs),
      new SimulationTracker(simSink, sessionId, 1000) // Sample every 1s
    ];
  }

  public getTracker<T extends Tracker>(type: new (...args: any[]) => T): T {
    const tracker = this.trackers.find(t => t instanceof type);
    if (!tracker) {
      throw new Error(`Tracker of type ${type.name} not found in RunContext`);
    }
    return tracker as T;
  }
}
