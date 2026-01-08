// CommandsDashboard module
export class CommandsDashboard {
  private gridToggleButton: HTMLButtonElement;
  private isGridVisible: boolean;
  private onToggleGrid: (visible: boolean) => void;
  private container: HTMLElement;

  constructor(container: HTMLElement, initialGridState: boolean, onToggleGrid: (visible: boolean) => void) {
    this.container = container;
    this.isGridVisible = initialGridState;
    this.onToggleGrid = onToggleGrid;
    this.gridToggleButton = document.createElement('button');
    this.gridToggleButton.id = 'toggleGridBtn';
    this.container.appendChild(this.gridToggleButton);
  }

  render(): void {
    this.gridToggleButton.textContent = this.isGridVisible ? 'Hide Grid' : 'Show Grid';
    this.gridToggleButton.onclick = () => {
      this.isGridVisible = !this.isGridVisible;
      this.gridToggleButton.textContent = this.isGridVisible ? 'Hide Grid' : 'Show Grid';
      this.onToggleGrid(this.isGridVisible);
    };
  }

  collapse(): void {
    this.container.style.height = '20px';
    this.container.style.overflow = 'hidden';
    this.container.innerHTML = ''; // Clear content
    const expandButton = document.createElement('button');
    expandButton.textContent = '+';
    expandButton.className = 'dashboard-expand-button';
    expandButton.onclick = () => this.expand();
    this.container.appendChild(expandButton);
  }

  expand(): void {
    this.container.style.height = '';
    this.container.style.overflow = '';
    // Remove expand button if present
    const expandBtn = this.container.querySelector('.dashboard-expand-button');
    if (expandBtn) {
      expandBtn.remove();
    }
    this.render(); // Re-render the dashboard content
  }
}
