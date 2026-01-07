// World singleton: holds simulation state and immutable config
import { worldConfig, Dimensions } from './config';

export interface WorldState {
  // Example state: add more as needed
  tick: number;
  totalTime: number;
  timer?: number;
}

export class World {
  public readonly config = worldConfig;
  public state: WorldState;
  private dimensions: any;
  
  constructor(dimensions?: Dimensions) {
    this.state = {
      tick: 0,
      totalTime: 0
    };
    this.dimensions = dimensions;
    console.log('>>> dimensions', dimensions);
  }
  step(time: number, delta: number) {
    this.state.tick += 1;
    this.state.totalTime += delta;
    this.state.timer = time;
    return this.state;
  }
}
