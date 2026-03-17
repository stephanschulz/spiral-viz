class SpiralVisualizer {
    constructor() {
        this.canvas = document.getElementById('spiralCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.tooltip = document.getElementById('tooltip');

        // Wall dimensions in meters
        this.wallWidth = 3.0;
        this.wallHeight = 3.0;

        // Spiral parameters
        this.spiralSpacing = 8.0;   // cm between spiral rounds
        this.segmentLength = 5.0;   // cm per segment
        this.tubeDiameter = 22;     // mm

        // LED parameters
        this.ledPitch = 1.67;       // cm between LEDs
        this.showLeds = true;

        // Display options
        this.showSegments = false;
        this.showGrid = true;
        this.showWallBorder = true;

        // View / pan / zoom
        this.scale = 1;
        this.offsetX = 0;
        this.offsetY = 0;
        this.isPanning = false;
        this.panStartX = 0;
        this.panStartY = 0;

        // Computed spiral data
        this.spiralPoints = [];
        this.spiralTotalLength = 0;
        this.spiralSegmentCount = 0;
        this.spiralLedCount = 0;
        this.spiralTurns = 0;

        this.init();
    }

    init() {
        this.setupEventListeners();
        window.addEventListener('resize', () => this.resizeCanvas());
        this.resizeCanvas();
        this.computeSpiral();
        this.draw();
    }

    setupEventListeners() {
        // Sliders
        const sliderIds = [
            'wallWidth', 'wallHeight', 'spiralSpacing',
            'segmentLength', 'tubeDiameter', 'ledPitch'
        ];
        sliderIds.forEach(id => {
            const el = document.getElementById(id);
            el.addEventListener('input', () => {
                this[id] = parseFloat(el.value);
                document.getElementById(id + 'Val').textContent =
                    id === 'tubeDiameter' ? el.value : parseFloat(el.value).toFixed(id === 'ledPitch' ? 2 : 1);
                this.computeSpiral();
                this.draw();
            });
        });

        // Checkboxes
        ['showLeds', 'showSegments', 'showGrid', 'showWallBorder'].forEach(id => {
            const el = document.getElementById(id);
            el.addEventListener('change', () => {
                this[id] = el.checked;
                this.draw();
            });
        });

        // Reset view
        document.getElementById('resetViewBtn').addEventListener('click', () => {
            this.scale = 1;
            this.offsetX = 0;
            this.offsetY = 0;
            this.draw();
        });

        // Pan & zoom
        this.canvas.addEventListener('mousedown', e => {
            this.isPanning = true;
            this.panStartX = e.clientX - this.offsetX;
            this.panStartY = e.clientY - this.offsetY;
        });
        this.canvas.addEventListener('mousemove', e => {
            if (this.isPanning) {
                this.offsetX = e.clientX - this.panStartX;
                this.offsetY = e.clientY - this.panStartY;
                this.draw();
            }
            this.handleTooltip(e);
        });
        this.canvas.addEventListener('mouseup', () => { this.isPanning = false; });
        this.canvas.addEventListener('mouseleave', () => {
            this.isPanning = false;
            this.tooltip.style.display = 'none';
        });
        this.canvas.addEventListener('wheel', e => {
            e.preventDefault();
            const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
            const rect = this.canvas.getBoundingClientRect();
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;
            // Zoom toward cursor
            this.offsetX = mx - (mx - this.offsetX) * zoomFactor;
            this.offsetY = my - (my - this.offsetY) * zoomFactor;
            this.scale *= zoomFactor;
            this.draw();
        }, { passive: false });
    }

    resizeCanvas() {
        const container = this.canvas.parentElement;
        this.canvas.width = container.clientWidth;
        this.canvas.height = container.clientHeight;
        this.draw();
    }

    // Convert world coordinates (meters) to canvas pixels
    worldToCanvas(wx, wy) {
        const wallMaxDim = Math.max(this.wallWidth, this.wallHeight);
        const canvasMinDim = Math.min(this.canvas.width, this.canvas.height);
        const ppm = (canvasMinDim * 0.85) / wallMaxDim; // pixels per meter
        const cx = this.canvas.width / 2 + this.offsetX;
        const cy = this.canvas.height / 2 + this.offsetY;
        return {
            x: cx + wx * ppm * this.scale,
            y: cy + wy * ppm * this.scale
        };
    }

    // Scale a world distance (meters) to canvas pixels
    worldScale(meters) {
        const wallMaxDim = Math.max(this.wallWidth, this.wallHeight);
        const canvasMinDim = Math.min(this.canvas.width, this.canvas.height);
        const ppm = (canvasMinDim * 0.85) / wallMaxDim;
        return meters * ppm * this.scale;
    }

    computeSpiral() {
        // Archimedean spiral: r = a + b*theta
        // b = spacing / (2*PI)  where spacing is distance between successive turns
        const spacingM = this.spiralSpacing / 100; // convert cm to meters
        const segLenM = this.segmentLength / 100;  // convert cm to meters
        const b = spacingM / (2 * Math.PI);

        // Maximum radius: half of the smaller wall dimension
        const maxRadius = Math.min(this.wallWidth, this.wallHeight) / 2 * 0.95;

        // Build spiral as a series of fixed-length segments
        this.spiralPoints = [{ x: 0, y: 0, theta: 0, r: 0 }];
        let theta = 0;
        let totalLength = 0;

        // Step along the spiral in small angular increments, accumulate arc length,
        // and place a segment point every segLenM meters.
        let accumLen = 0;
        const dTheta = 0.01; // small angular step for arc-length integration

        while (true) {
            const r = b * theta;
            const nextTheta = theta + dTheta;
            const rNext = b * nextTheta;
            // Approximate arc length for this small step
            // ds = sqrt( (dr)^2 + (r*dTheta)^2 )
            const dr = rNext - r;
            const ds = Math.sqrt(dr * dr + (r * dTheta) * (r * dTheta));
            accumLen += ds;

            if (accumLen >= segLenM) {
                const x = rNext * Math.cos(nextTheta);
                const y = rNext * Math.sin(nextTheta);
                this.spiralPoints.push({ x, y, theta: nextTheta, r: rNext });
                totalLength += accumLen;
                accumLen = 0;
            }

            theta = nextTheta;

            if (rNext > maxRadius) {
                // Add final partial segment if meaningful
                if (accumLen > segLenM * 0.1) {
                    const x = rNext * Math.cos(theta);
                    const y = rNext * Math.sin(theta);
                    this.spiralPoints.push({ x, y, theta, r: rNext });
                    totalLength += accumLen;
                }
                break;
            }
        }

        this.spiralTotalLength = totalLength;
        this.spiralSegmentCount = Math.max(0, this.spiralPoints.length - 1);
        this.spiralTurns = theta / (2 * Math.PI);
        this.spiralLedCount = Math.floor(totalLength / (this.ledPitch / 100));

        // Update info
        document.getElementById('spiralLength').textContent =
            `Spiral Length: ${this.spiralTotalLength.toFixed(2)} m (${(this.spiralTotalLength * 100).toFixed(1)} cm)`;
        document.getElementById('segmentCount').textContent =
            `Segments: ${this.spiralSegmentCount}`;
        document.getElementById('ledCount').textContent =
            `Total LEDs: ${this.spiralLedCount}`;
        document.getElementById('turnsCount').textContent =
            `Turns: ${this.spiralTurns.toFixed(1)}`;
        document.getElementById('infoBox').textContent =
            `Tube diameter: ${this.tubeDiameter} mm\n` +
            `Spiral spacing: ${this.spiralSpacing} cm\n` +
            `Segment length: ${this.segmentLength} cm\n` +
            `LED pitch: ${this.ledPitch} cm\n` +
            `LEDs per segment: ${(this.segmentLength / this.ledPitch).toFixed(1)}\n` +
            `Wall: ${this.wallWidth} x ${this.wallHeight} m`;
    }

    draw() {
        const ctx = this.ctx;
        ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Background
        ctx.fillStyle = '#f5f5f5';
        ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        this.drawGrid();
        this.drawWall();
        this.drawSpiral();
    }

    drawGrid() {
        if (!this.showGrid) return;
        const ctx = this.ctx;
        ctx.save();
        ctx.strokeStyle = '#e0e0e0';
        ctx.lineWidth = 1;

        // Draw grid lines every 0.5m across the wall area (and a bit beyond)
        const step = 0.5; // meters
        const extent = Math.max(this.wallWidth, this.wallHeight) / 2 + 0.5;
        for (let v = -extent; v <= extent; v += step) {
            // Vertical lines
            const p1 = this.worldToCanvas(v, -extent);
            const p2 = this.worldToCanvas(v, extent);
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
            // Horizontal lines
            const p3 = this.worldToCanvas(-extent, v);
            const p4 = this.worldToCanvas(extent, v);
            ctx.beginPath();
            ctx.moveTo(p3.x, p3.y);
            ctx.lineTo(p4.x, p4.y);
            ctx.stroke();
        }
        ctx.restore();
    }

    drawWall() {
        if (!this.showWallBorder) return;
        const ctx = this.ctx;
        const hw = this.wallWidth / 2;
        const hh = this.wallHeight / 2;

        const tl = this.worldToCanvas(-hw, -hh);
        const br = this.worldToCanvas(hw, hh);

        ctx.save();
        ctx.strokeStyle = '#333';
        ctx.lineWidth = 2;
        ctx.setLineDash([8, 4]);
        ctx.strokeRect(tl.x, tl.y, br.x - tl.x, br.y - tl.y);
        ctx.setLineDash([]);

        // Label
        ctx.fillStyle = '#555';
        ctx.font = '11px -apple-system, sans-serif';
        ctx.fillText(`${this.wallWidth}m x ${this.wallHeight}m`, tl.x + 4, tl.y - 6);
        ctx.restore();
    }

    drawSpiral() {
        if (this.spiralPoints.length < 2) return;
        const ctx = this.ctx;
        const tubeRadiusM = (this.tubeDiameter / 1000) / 2; // tube radius in meters

        // Draw the two edges of the tube (outer and inner offset from centerline)
        ctx.save();

        // Draw tube body as a filled path between outer and inner edges
        const outerPts = [];
        const innerPts = [];

        for (let i = 0; i < this.spiralPoints.length; i++) {
            const p = this.spiralPoints[i];
            // Normal direction: perpendicular to the tangent
            let nx, ny;
            if (i < this.spiralPoints.length - 1) {
                const pNext = this.spiralPoints[i + 1];
                const dx = pNext.x - p.x;
                const dy = pNext.y - p.y;
                const len = Math.sqrt(dx * dx + dy * dy);
                nx = -dy / len;
                ny = dx / len;
            } else {
                const pPrev = this.spiralPoints[i - 1];
                const dx = p.x - pPrev.x;
                const dy = p.y - pPrev.y;
                const len = Math.sqrt(dx * dx + dy * dy);
                nx = -dy / len;
                ny = dx / len;
            }
            outerPts.push({
                x: p.x + nx * tubeRadiusM,
                y: p.y + ny * tubeRadiusM
            });
            innerPts.push({
                x: p.x - nx * tubeRadiusM,
                y: p.y - ny * tubeRadiusM
            });
        }

        // Fill tube body
        ctx.beginPath();
        let cp = this.worldToCanvas(outerPts[0].x, outerPts[0].y);
        ctx.moveTo(cp.x, cp.y);
        for (let i = 1; i < outerPts.length; i++) {
            cp = this.worldToCanvas(outerPts[i].x, outerPts[i].y);
            ctx.lineTo(cp.x, cp.y);
        }
        for (let i = innerPts.length - 1; i >= 0; i--) {
            cp = this.worldToCanvas(innerPts[i].x, innerPts[i].y);
            ctx.lineTo(cp.x, cp.y);
        }
        ctx.closePath();
        ctx.fillStyle = 'rgba(200, 220, 255, 0.3)';
        ctx.fill();

        // Draw outer edge
        ctx.beginPath();
        cp = this.worldToCanvas(outerPts[0].x, outerPts[0].y);
        ctx.moveTo(cp.x, cp.y);
        for (let i = 1; i < outerPts.length; i++) {
            cp = this.worldToCanvas(outerPts[i].x, outerPts[i].y);
            ctx.lineTo(cp.x, cp.y);
        }
        ctx.strokeStyle = '#2266cc';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Draw inner edge
        ctx.beginPath();
        cp = this.worldToCanvas(innerPts[0].x, innerPts[0].y);
        ctx.moveTo(cp.x, cp.y);
        for (let i = 1; i < innerPts.length; i++) {
            cp = this.worldToCanvas(innerPts[i].x, innerPts[i].y);
            ctx.lineTo(cp.x, cp.y);
        }
        ctx.strokeStyle = '#2266cc';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Draw segment joints
        if (this.showSegments) {
            for (let i = 0; i < this.spiralPoints.length; i++) {
                const po = this.worldToCanvas(outerPts[i].x, outerPts[i].y);
                const pi2 = this.worldToCanvas(innerPts[i].x, innerPts[i].y);
                ctx.beginPath();
                ctx.moveTo(po.x, po.y);
                ctx.lineTo(pi2.x, pi2.y);
                ctx.strokeStyle = 'rgba(255, 100, 50, 0.5)';
                ctx.lineWidth = 1;
                ctx.stroke();
            }
        }

        // Draw LEDs
        if (this.showLeds) {
            const ledPitchM = this.ledPitch / 100;
            let accumDist = 0;

            for (let i = 1; i < this.spiralPoints.length; i++) {
                const prev = this.spiralPoints[i - 1];
                const curr = this.spiralPoints[i];
                const dx = curr.x - prev.x;
                const dy = curr.y - prev.y;
                const segLen = Math.sqrt(dx * dx + dy * dy);
                if (segLen === 0) continue;

                const ux = dx / segLen;
                const uy = dy / segLen;

                let d = ledPitchM - accumDist;
                while (d <= segLen) {
                    const lx = prev.x + ux * d;
                    const ly = prev.y + uy * d;
                    const lp = this.worldToCanvas(lx, ly);
                    const ledSize = Math.max(2, this.worldScale(0.005));
                    ctx.beginPath();
                    ctx.arc(lp.x, lp.y, ledSize, 0, Math.PI * 2);
                    ctx.fillStyle = '#ffcc00';
                    ctx.fill();
                    ctx.strokeStyle = '#cc9900';
                    ctx.lineWidth = 0.5;
                    ctx.stroke();
                    d += ledPitchM;
                }
                accumDist = segLen - (d - ledPitchM);
            }
        }

        // Draw center point
        const center = this.worldToCanvas(0, 0);
        ctx.beginPath();
        ctx.arc(center.x, center.y, 4, 0, Math.PI * 2);
        ctx.fillStyle = '#dc3545';
        ctx.fill();

        ctx.restore();
    }

    handleTooltip(e) {
        if (this.isPanning) {
            this.tooltip.style.display = 'none';
            return;
        }
        const rect = this.canvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;

        // Find closest spiral point
        let minDist = Infinity;
        let closestIdx = -1;
        for (let i = 0; i < this.spiralPoints.length; i++) {
            const cp = this.worldToCanvas(this.spiralPoints[i].x, this.spiralPoints[i].y);
            const d = Math.sqrt((cp.x - mx) ** 2 + (cp.y - my) ** 2);
            if (d < minDist) {
                minDist = d;
                closestIdx = i;
            }
        }

        if (minDist < 30 && closestIdx >= 0) {
            const p = this.spiralPoints[closestIdx];
            // Compute cumulative length up to this point
            let cumLen = 0;
            for (let i = 1; i <= closestIdx; i++) {
                const prev = this.spiralPoints[i - 1];
                const curr = this.spiralPoints[i];
                cumLen += Math.sqrt((curr.x - prev.x) ** 2 + (curr.y - prev.y) ** 2);
            }
            this.tooltip.style.display = 'block';
            this.tooltip.style.left = (e.clientX + 12) + 'px';
            this.tooltip.style.top = (e.clientY + 12) + 'px';
            this.tooltip.textContent =
                `Segment: ${closestIdx} / ${this.spiralSegmentCount}\n` +
                `Radius: ${(p.r * 100).toFixed(1)} cm\n` +
                `Length to here: ${cumLen.toFixed(2)} m\n` +
                `Angle: ${(p.theta * 180 / Math.PI).toFixed(1)}°`;
        } else {
            this.tooltip.style.display = 'none';
        }
    }
}

// Initialize
const app = new SpiralVisualizer();
