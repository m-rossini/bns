
import Phaser from 'phaser';
import { graphicsConfig } from './config';



// Dynamically set container widths based on config
function setContainerWidths() {
  const mainContainer = document.getElementById('mainContainer');
  const appDiv = document.getElementById('app');
  const optionsFrame = document.getElementById('optionsFrame');
  if (mainContainer) mainContainer.style.width = graphicsConfig.canvasWidth + 'px';
  if (appDiv) appDiv.style.width = graphicsConfig.canvasWidth + 'px';
  if (optionsFrame) optionsFrame.style.width = graphicsConfig.canvasWidth + 'px';
}
setContainerWidths();

const config: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,
  width: graphicsConfig.canvasWidth,
  height: graphicsConfig.canvasHeight,
  backgroundColor: graphicsConfig.canvasBackgroundColor,
  parent: 'app',
  scene: {
    create() {
      const gridGraphics = this.add.graphics();
      const drawGridFn = (show: boolean) => drawGrid(gridGraphics, show);
      drawGridFn(graphicsConfig.showGrid);
      setupGridToggle(drawGridFn);
    }
  }
};

function drawGrid(gridGraphics: Phaser.GameObjects.Graphics, show: boolean) {
  gridGraphics.clear();
  if (!show) return;
  const step = graphicsConfig.gridStep ?? 40;
  if (graphicsConfig.gridDrawMode === 'rects') {
    drawGridRects(gridGraphics, step);
  } else {
    drawGridLines(gridGraphics, step);
  }
}

function drawGridRects(gridGraphics: Phaser.GameObjects.Graphics, step: number) {
  // TODO We should fill rectangles based on season of the year and temperature of the environment
  for (let x = 0; x < graphicsConfig.canvasWidth; x += step) {
    for (let y = 0; y < graphicsConfig.canvasHeight; y += step) {
      // Generate a random color for each square
      const color = Phaser.Display.Color.RandomRGB();
      gridGraphics.fillStyle(color.color, 0.8);
      gridGraphics.fillRect(x, y, step, step);
    }
  }
}

function drawGridLines(gridGraphics: Phaser.GameObjects.Graphics, step: number) {
  const thickness = graphicsConfig.gridLineThickness ?? 1;
  const alpha = graphicsConfig.gridLineAlpha ?? 0.7;
  gridGraphics.lineStyle(thickness, Phaser.Display.Color.HexStringToColor(graphicsConfig.gridColor).color, alpha);
  for (let x = 0; x <= graphicsConfig.canvasWidth; x += step) {
    gridGraphics.lineBetween(x, 0, x, graphicsConfig.canvasHeight);
  }
  for (let y = 0; y <= graphicsConfig.canvasHeight; y += step) {
    gridGraphics.lineBetween(0, y, graphicsConfig.canvasWidth, y);
  }
}

function setupGridToggle(drawGridFn: (show: boolean) => void) {
  setTimeout(() => {
    setContainerWidths(); // Ensure widths are correct after DOM is ready
    const btn = document.getElementById('toggleGridBtn');
    if (btn) {
      btn.textContent = graphicsConfig.showGrid ? 'Hide Grid' : 'Show Grid';
      btn.style.fontFamily = graphicsConfig.defaultFontFamily ?? 'Arial';
      btn.onclick = () => {
        graphicsConfig.showGrid = !graphicsConfig.showGrid;
        btn.textContent = graphicsConfig.showGrid ? 'Hide Grid' : 'Show Grid';
        drawGridFn(graphicsConfig.showGrid);
      };
    }
  }, 100);
}



new Phaser.Game(config);
