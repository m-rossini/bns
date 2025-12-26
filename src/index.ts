import Phaser from 'phaser';

const config: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,
  width: 800,
  height: 600,
  backgroundColor: '#222',
  scene: {
    create() {
      this.add.text(300, 250, 'Bean World Startup', { font: '32px Arial', color: '#fff' });
    }
  }
};

new Phaser.Game(config);
