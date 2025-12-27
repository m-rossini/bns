import Phaser from 'phaser/dist/phaser.min.js';
import { loadAllConfigs } from './config/ConfigLoader';

const { world: worldConfig, bean: beanConfig, tradeoffs: tradeoffConfig } = loadAllConfigs();

const config: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,
  width: worldConfig.width,
  height: worldConfig.height,
  backgroundColor: worldConfig.background_color,
  scene: {
    create() {
      this.add.text(
        (worldConfig.width / 2) - 100,
        (worldConfig.height / 2) - 32,
        'Bean World Startup',
        { font: '32px Arial', color: '#fff' }
      );
    }
  }
};
console.info(5, worldConfig.background_color)
console.info(10, 'Phaser Config->', config)
new Phaser.Game(config);
