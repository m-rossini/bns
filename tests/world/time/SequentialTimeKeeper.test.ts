import { describe, it, expect } from 'vitest';
import { SequentialTimeKeeper } from '../../../src/world/time/SequentialTimeKeeper';

describe('SequentialTimeKeeper', () => {
  it('should initialize with provided ticks', () => {
    const tk = new SequentialTimeKeeper({ ticksPerYear: 360, initialTicks: 100 });
    expect(tk.getTicks()).toBe(100);
    expect(tk.getTicksPerYear()).toBe(360);
  });

  it('should increment ticks on tick()', () => {
    const tk = new SequentialTimeKeeper({ ticksPerYear: 360 });
    tk.tick();
    expect(tk.getTicks()).toBe(1);
    tk.tick();
    expect(tk.getTicks()).toBe(2);
  });

  it('should calculate year progress correctly', () => {
    const tk = new SequentialTimeKeeper({ ticksPerYear: 360 });
    
    // Day 0 (start of year)
    expect(tk.getYearProgress()).toBe(0/360);
    
    // Half year
    for (let i = 0; i < 180; i++) tk.tick();
    expect(tk.getYearProgress()).toBe(180/360);
    
    // Nearly end of year
    for (let i = 0; i < 179; i++) tk.tick();
    expect(tk.getYearProgress()).toBe(359/360);
    
    // Start of next year
    tk.tick(); // total 360
    expect(tk.getYearProgress()).toBe(0);
  });

  it('should calculate total years correctly', () => {
    const tk = new SequentialTimeKeeper({ ticksPerYear: 100 });
    
    expect(tk.getTotalYears()).toBe(0);
    
    for (let i = 0; i < 100; i++) tk.tick();
    expect(tk.getTotalYears()).toBe(1);
    
    for (let i = 0; i < 150; i++) tk.tick();
    expect(tk.getTotalYears()).toBe(2);
  });
});
