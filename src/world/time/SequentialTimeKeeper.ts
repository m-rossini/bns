import { ITimeKeeper } from '@/world/simulationTypes';

export class SequentialTimeKeeper implements ITimeKeeper {
  private ticks: number;
  private readonly ticksPerYear: number;

  constructor(params: { ticksPerYear: number; initialTicks?: number }) {
    this.ticks = params.initialTicks ?? 0;
    this.ticksPerYear = params.ticksPerYear;
  }

  tick(): void {
    this.ticks++;
  }

  getTicks(): number {
    return this.ticks;
  }

  getYearProgress(): number {
    return (this.ticks % this.ticksPerYear) / this.ticksPerYear;
  }

  getTotalYears(): number {
    return Math.floor(this.ticks / this.ticksPerYear);
  }

  getTicksPerYear(): number {
    return this.ticksPerYear;
  }
}
