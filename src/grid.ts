import type { GameObjects } from 'phaser';
import { WorldWindowConfig } from './config';

export function drawGrid(
  gridGraphics: GameObjects.Graphics,
  showGrid: boolean,
  config: WorldWindowConfig
) {
  gridGraphics.clear();
  const step = config.cellSize ?? 40;
  const alpha = config.gridLineAlpha ?? 0.7;
  if (!showGrid) {
    return;
  }
  if (config.gridDrawMode === 'rects') {
    drawGridRects(gridGraphics, step, alpha, config);
  } else {
    drawGridLines(gridGraphics, step, alpha, config);
  }
}

function drawGridRects(
  gridGraphics: GameObjects.Graphics,
  step: number,
  alpha: number,
  config: WorldWindowConfig
) {
  // TODO We should fill rectangles based on season of the year and temperature of the environment
  for (let x = 0; x < config.canvasWidth; x += step) {
    for (let y = 0; y < config.canvasHeight; y += step) {
      gridGraphics.fillStyle(randomColor(), alpha);
      gridGraphics.fillRect(x, y, step, step);
    }
  }
}

function drawGridLines(
  gridGraphics: GameObjects.Graphics,
  step: number,
  alpha: number,
  config: WorldWindowConfig
) {
  const thickness = config.gridLineThickness ?? 1;
  gridGraphics.lineStyle(
    thickness,
    hexToColor(config.gridColor),
    alpha
  );
  for (let x = 0; x <= config.canvasWidth; x += step) {
    gridGraphics.lineBetween(x, 0, x, config.canvasHeight);
  }
  for (let y = 0; y <= config.canvasHeight; y += step) {
    gridGraphics.lineBetween(0, y, config.canvasWidth, y);
  }
}

function randomColor(): number {
  return Math.floor(Math.random() * 0xffffff);
}

function hexToColor(hex: string): number {
  const normalized = hex.replace(/^#/, '');
  return Number.parseInt(normalized, 16);
}
