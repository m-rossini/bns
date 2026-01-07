
import Phaser from 'phaser';
import { worldWindow } from './worldWindow';
import { SimulationStatsDashboard } from './dashboards/SimulationStatsDashboard';
import { StatsDashboard } from './dashboards/StatsDashboard';
import { DynamicConfigDashboard } from './dashboards/DynamicConfigDashboard';
import { CommandsDashboard } from './dashboards/CommandsDashboard';



// Dynamically set container widths based on config
function setContainerWidths() {
  const width = worldWindow.config.canvasWidth;
  const mainContainer = document.getElementById('mainContainer');
  const appDiv = document.getElementById('app');
  const optionsFrame = document.getElementById('optionsFrame');
  if (mainContainer) mainContainer.style.width = width + 'px';
  if (appDiv) appDiv.style.width = width + 'px';
  if (optionsFrame) optionsFrame.style.width = width + 'px';
}

const config: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,
  width: worldWindow.config.canvasWidth,
  height: worldWindow.config.canvasHeight,
  backgroundColor: worldWindow.config.canvasBackgroundColor,
  parent: 'app',
  scene: {
    create() {
      const gridGraphics = this.add.graphics();
      const drawGridFn = (show: boolean) => drawGrid(gridGraphics, show);
      drawGridFn(worldWindow.state.showGrid);

      // Instantiate dashboards in new layout

      const statsDashboard = new StatsDashboard();
      statsDashboard.render();

      const dynamicConfigDashboard = new DynamicConfigDashboard();
      dynamicConfigDashboard.render();

      const actionsFrame = document.getElementById('actionsFrame');
      const commandsDashboard = new CommandsDashboard(
        actionsFrame!,
        worldWindow.state.showGrid,
        (newShowGrid: boolean) => {
          worldWindow.state.showGrid = newShowGrid;
          drawGridFn(worldWindow.state.showGrid);
        }
      );
      commandsDashboard.render();
    },
    update(time: number, delta: number) {
      worldWindow.update(time, delta);
    }
  }
};

function drawGrid(gridGraphics: Phaser.GameObjects.Graphics, showGrid: boolean) {
  gridGraphics.clear();
  const step = worldWindow.config.cellSize ?? 40;
  const alpha = worldWindow.config.gridLineAlpha ?? 0.7;
  if (!showGrid) return;
  if (worldWindow.config.gridDrawMode === 'rects') {
    drawGridRects(gridGraphics, step, alpha);
  } else {
    drawGridLines(gridGraphics, step, alpha);
  }
}

function drawGridRects(gridGraphics: Phaser.GameObjects.Graphics, step: number, alpha: number) {
  // TODO We should fill rectangles based on season of the year and temperature of the environment
  for (let x = 0; x < worldWindow.config.canvasWidth; x += step) {
    for (let y = 0; y < worldWindow.config.canvasHeight; y += step) {
      // Generate a random color for each square
      const color = Phaser.Display.Color.RandomRGB();
      gridGraphics.fillStyle(color.color, alpha);
      gridGraphics.fillRect(x, y, step, step);
    }
  }
}

function drawGridLines(gridGraphics: Phaser.GameObjects.Graphics, step: number, alpha: number) {
  const thickness = worldWindow.config.gridLineThickness ?? 1;
  gridGraphics.lineStyle(thickness, Phaser.Display.Color.HexStringToColor(worldWindow.config.gridColor).color, alpha);
  for (let x = 0; x <= worldWindow.config.canvasWidth; x += step) {
    gridGraphics.lineBetween(x, 0, x, worldWindow.config.canvasHeight);
  }
  for (let y = 0; y <= worldWindow.config.canvasHeight; y += step) {
    gridGraphics.lineBetween(0, y, worldWindow.config.canvasWidth, y);
  }
}

new Phaser.Game(config);
