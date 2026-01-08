import { beforeEach, describe, expect, it, vi } from 'vitest';
import { drawGrid } from '../src/grid';
import { WorldWindowConfig } from '../src/config';

const baseConfig: WorldWindowConfig = {
  canvasWidth: 120,
  canvasHeight: 80,
  canvasBackgroundColor: '#000000',
  gridColor: '#efde74',
  gridLineThickness: 1,
  gridLineAlpha: 0.7,
  defaultFontFamily: 'Arial',
  cellSize: 20,
  gridDrawMode: 'lines'
};

describe('drawGrid helper', () => {
  let gridGraphics: any;

  beforeEach(() => {
    gridGraphics = {
      clear: vi.fn(),
      lineStyle: vi.fn(),
      lineBetween: vi.fn(),
      fillStyle: vi.fn(),
      fillRect: vi.fn()
    } as any;
  });

  it('clears the canvas and skips drawing when grid is hidden', () => {
    drawGrid(gridGraphics, false, baseConfig);
    expect(gridGraphics.clear).toHaveBeenCalledTimes(1);
    expect(gridGraphics.lineStyle).not.toHaveBeenCalled();
    expect(gridGraphics.lineBetween).not.toHaveBeenCalled();
    expect(gridGraphics.fillRect).not.toHaveBeenCalled();
  });

  it('draws lines when grid is enabled', () => {
    drawGrid(gridGraphics, true, baseConfig);
    expect(gridGraphics.clear).toHaveBeenCalled();
    expect(gridGraphics.lineStyle).toHaveBeenCalledTimes(1);
    expect(gridGraphics.lineBetween).toHaveBeenCalled();
    expect(gridGraphics.fillRect).not.toHaveBeenCalled();
  });

  it('draws rectangles when configured to do so', () => {
    const rectConfig: WorldWindowConfig = { ...baseConfig, gridDrawMode: 'rects' };
    drawGrid(gridGraphics, true, rectConfig);
    expect(gridGraphics.clear).toHaveBeenCalled();
    expect(gridGraphics.fillRect).toHaveBeenCalled();
    expect(gridGraphics.lineBetween).not.toHaveBeenCalled();
  });
});
