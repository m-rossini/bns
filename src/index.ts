
import Phaser from 'phaser';
import { graphicsConfig } from './config';


const config: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,
  width: graphicsConfig.canvasWidth,
  height: graphicsConfig.canvasHeight,
  backgroundColor: graphicsConfig.backgroundColor,
  parent: 'app',
  scene: {
    create() {
      // Draw grid if enabled
      const gridGraphics = this.add.graphics();
      function drawGrid(show: boolean) {
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
      drawGrid(graphicsConfig.showGrid);

      // HTML toggle button below canvas
      setTimeout(() => {
        const btn = document.getElementById('toggleGridBtn');
        if (btn) {
          btn.textContent = graphicsConfig.showGrid ? 'Hide Grid' : 'Show Grid';
          btn.onclick = () => {
            graphicsConfig.showGrid = !graphicsConfig.showGrid;
            btn.textContent = graphicsConfig.showGrid ? 'Hide Grid' : 'Show Grid';
            drawGrid(graphicsConfig.showGrid);
          };
        }
      }, 100);

      // Title text
      this.add.text(
        graphicsConfig.canvasWidth / 2 - 100,
        graphicsConfig.canvasHeight / 2 - 50,
        'Bean World Startup',
        { font: '32px Arial', color: '#fff' }
      );
    }
  }
};

new Phaser.Game(config);
