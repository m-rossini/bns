
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
  backgroundColor: graphicsConfig.backgroundColor,
  parent: 'app',
  scene: {
    create() {
      const gridGraphics = this.add.graphics();
      const drawGridFn = (show: boolean) => drawGrid(gridGraphics, show);
      drawGridFn(graphicsConfig.showGrid);
      setupGridToggle(drawGridFn);
      renderTitle(this);
    }
  }
};

function drawGrid(gridGraphics: Phaser.GameObjects.Graphics, show: boolean) {
  gridGraphics.clear();
  if (!show) return;
  gridGraphics.lineStyle(1, Phaser.Display.Color.HexStringToColor(graphicsConfig.gridColor).color, 0.7);
  const step = 40;
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
      btn.onclick = () => {
        graphicsConfig.showGrid = !graphicsConfig.showGrid;
        btn.textContent = graphicsConfig.showGrid ? 'Hide Grid' : 'Show Grid';
        drawGridFn(graphicsConfig.showGrid);
      };
    }
  }, 100);
}

function renderTitle(scene: Phaser.Scene) {
  scene.add.text(
    graphicsConfig.canvasWidth / 2 - 100,
    graphicsConfig.canvasHeight / 2 - 50,
    'Bean World Startup',
    { font: '32px Arial', color: '#fff' }
  );
}

new Phaser.Game(config);
