export class CommandsDashboard {
  private gridToggleButton: HTMLButtonElement;
  private collapseButton: HTMLButtonElement;
  private isGridVisible: boolean;
  private onToggleGrid: (visible: boolean) => void;
  private container: HTMLElement;
  private contentWrapper: HTMLDivElement;
  private header: HTMLDivElement;

  constructor(container: HTMLElement, initialGridState: boolean, onToggleGrid: (visible: boolean) => void) {
    this.container = container;
    this.isGridVisible = initialGridState;
    this.onToggleGrid = onToggleGrid;
    
    // Create header with collapse button
    this.header = document.createElement('div');
    this.header.style.cssText = 'display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;';
    
    const title = document.createElement('h2');
    title.textContent = 'Commands';
    title.style.margin = '0';
    
    this.collapseButton = document.createElement('button');
    this.collapseButton.textContent = '▶';
    this.collapseButton.className = 'dashboard-collapse-btn';
    this.collapseButton.onclick = () => this.collapse();
    
    this.header.appendChild(title);
    this.header.appendChild(this.collapseButton);
    this.container.appendChild(this.header);
    
    // Create vertical title for collapsed state
    const verticalTitle = document.createElement('h2');
    verticalTitle.textContent = 'Commands';
    verticalTitle.style.margin = '0';
    verticalTitle.style.writingMode = 'vertical-rl';
    verticalTitle.style.transform = 'rotate(180deg)';
    verticalTitle.style.display = 'none';
    verticalTitle.className = 'vertical-title';
    this.header.appendChild(verticalTitle);
    
    // Create content wrapper
    this.contentWrapper = document.createElement('div');
    this.container.appendChild(this.contentWrapper);
    
    this.gridToggleButton = document.createElement('button');
    this.gridToggleButton.id = 'toggleGridBtn';
    this.contentWrapper.appendChild(this.gridToggleButton);
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
    this.contentWrapper.style.display = 'none';
    this.collapseButton.textContent = '◀';
    this.collapseButton.onclick = () => this.expand();
    // Collapse horizontally
    this.container.style.width = '50px';
    this.container.style.padding = '16px 8px';
    this.header.style.flexDirection = 'column';
    this.header.style.alignItems = 'center';
    this.header.style.justifyContent = 'flex-start';
    
    // Hide horizontal title, show vertical title
    const regularTitle = this.header.querySelector('h2:not(.vertical-title)');
    const verticalTitle = this.header.querySelector('.vertical-title');
    if (regularTitle) (regularTitle as HTMLElement).style.display = 'none';
    if (verticalTitle) (verticalTitle as HTMLElement).style.display = 'block';
  }

  expand(): void {
    this.contentWrapper.style.display = 'block';
    this.collapseButton.textContent = '▶';
    this.collapseButton.onclick = () => this.collapse();
    // Restore original width
    this.container.style.width = '';
    this.container.style.padding = '';
    this.header.style.flexDirection = '';
    this.header.style.alignItems = '';
    this.header.style.justifyContent = '';
    
    // Show horizontal title, hide vertical title
    const regularTitle = this.header.querySelector('h2:not(.vertical-title)');
    const verticalTitle = this.header.querySelector('.vertical-title');
    if (regularTitle) (regularTitle as HTMLElement).style.display = 'block';
    if (verticalTitle) (verticalTitle as HTMLElement).style.display = 'none';
  }
}