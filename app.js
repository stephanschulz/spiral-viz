class SpiralVisualizer {
    constructor() {
        this.canvas = document.getElementById('spiralCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.tooltip = document.getElementById('tooltip');

        // Wall dimensions in meters
        this.wallWidth = 3.0;
        this.wallHeight = 3.0;

        // Spiral parameters (GUI units)
        this.spiralSpacing = 22;    // mm between spiral rounds
        this.segmentLength = 200;   // cm per segment
        this.tubeDiameter = 22;     // mm

        // LED parameters (GUI units)
        this.ledPitch = 10.4;       // mm between LEDs
        this.showLeds = true;

        // Display options
        this.showSegments = true;
        this.showGrid = true;
        this.showWallBorder = true;

        // View / pan / zoom
        // originX/originY = screen position of world (0,0)
        this.scale = 1;
        this.originX = 0;
        this.originY = 0;
        this.isPanning = false;
        this.panStartX = 0;
        this.panStartY = 0;

        // Computed spiral data
        this.curvePoints = [];       // dense points along the spiral curve (in meters)
        this.segmentIndices = [];    // indices into curvePoints where segments begin/end
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
        const sliderConfigs = {
            wallWidth:     { decimals: 1 },
            wallHeight:    { decimals: 1 },
            spiralSpacing: { decimals: 0 },
            segmentLength: { decimals: 0 },
            tubeDiameter:  { decimals: 0 },
            ledPitch:      { decimals: 1 },
        };
        Object.keys(sliderConfigs).forEach(id => {
            const el = document.getElementById(id);
            const cfg = sliderConfigs[id];
            el.addEventListener('input', () => {
                this[id] = parseFloat(el.value);
                document.getElementById(id + 'Val').textContent =
                    parseFloat(el.value).toFixed(cfg.decimals);
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
            this.originX = this.canvas.width / 2;
            this.originY = this.canvas.height / 2;
            this.draw();
        });

        // Pan & zoom
        this.canvas.addEventListener('mousedown', e => {
            this.isPanning = true;
            this.panStartX = e.clientX - this.originX;
            this.panStartY = e.clientY - this.originY;
        });
        this.canvas.addEventListener('mousemove', e => {
            if (this.isPanning) {
                this.originX = e.clientX - this.panStartX;
                this.originY = e.clientY - this.panStartY;
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
            // Zoom centered on mouse: keep the world point under cursor fixed
            this.originX = mx - (mx - this.originX) * zoomFactor;
            this.originY = my - (my - this.originY) * zoomFactor;
            this.scale *= zoomFactor;
            this.draw();
        }, { passive: false });
    }

    resizeCanvas() {
        const container = this.canvas.parentElement;
        const oldW = this.canvas.width;
        const oldH = this.canvas.height;
        this.canvas.width = container.clientWidth;
        this.canvas.height = container.clientHeight;
        if (!this._initializedOrigin) {
            this.originX = this.canvas.width / 2;
            this.originY = this.canvas.height / 2;
            this._initializedOrigin = true;
        } else {
            this.originX += (this.canvas.width - oldW) / 2;
            this.originY += (this.canvas.height - oldH) / 2;
        }
        this.draw();
    }

    worldToCanvas(wx, wy) {
        const ppm = this.getPPM();
        return {
            x: this.originX + wx * ppm * this.scale,
            y: this.originY + wy * ppm * this.scale
        };
    }

    getPPM() {
        const wallMaxDim = Math.max(this.wallWidth, this.wallHeight);
        const canvasMinDim = Math.min(this.canvas.width, this.canvas.height);
        return (canvasMinDim * 0.85) / wallMaxDim;
    }

    worldScale(meters) {
        return meters * this.getPPM() * this.scale;
    }

    computeSpiral() {
        // Archimedean spiral: r = b * theta
        // spacing = gap between tube edges, so center-to-center = gap + tubeDiameter
        const gapM = this.spiralSpacing / 1000;          // mm -> meters
        const tubeDiamM = this.tubeDiameter / 1000;      // mm -> meters
        const centerToCenter = gapM + tubeDiamM;         // center-to-center between turns
        const segLenM = this.segmentLength / 100;         // cm -> meters
        const b = centerToCenter / (2 * Math.PI);

        const maxRadius = Math.min(this.wallWidth, this.wallHeight) / 2 * 0.95;

        // Generate dense curve points for smooth rendering
        // Use a small angular step that produces ~2mm arc steps
        this.curvePoints = [{ x: 0, y: 0, theta: 0, r: 0 }];
        this.segmentIndices = [0]; // first segment starts at index 0

        let theta = 0;
        let totalLength = 0;
        let segAccum = 0;  // accumulated length toward next segment boundary
        const targetStep = 0.002; // ~2mm arc step for smoothness

        while (true) {
            const r = b * theta;
            // Adaptive angular step: ds ≈ r * dTheta for large r
            // For small r, use a fixed small angle
            let dTheta;
            if (r < 0.001) {
                dTheta = 0.05;
            } else {
                dTheta = targetStep / r;
                dTheta = Math.min(dTheta, 0.05);
                dTheta = Math.max(dTheta, 0.001);
            }

            const nextTheta = theta + dTheta;
            const rNext = b * nextTheta;

            // Arc length for this step
            const dr = rNext - r;
            const ds = Math.sqrt(dr * dr + (r * dTheta) * (r * dTheta));

            totalLength += ds;
            segAccum += ds;

            const x = rNext * Math.cos(nextTheta);
            const y = rNext * Math.sin(nextTheta);
            this.curvePoints.push({ x, y, theta: nextTheta, r: rNext });

            // Check if we crossed a segment boundary
            if (segAccum >= segLenM) {
                this.segmentIndices.push(this.curvePoints.length - 1);
                segAccum = 0;
            }

            theta = nextTheta;

            if (rNext > maxRadius) break;
        }

        // Add final index as last segment boundary
        const lastIdx = this.curvePoints.length - 1;
        if (this.segmentIndices[this.segmentIndices.length - 1] !== lastIdx) {
            this.segmentIndices.push(lastIdx);
        }

        this.spiralTotalLength = totalLength;
        this.spiralSegmentCount = Math.max(0, this.segmentIndices.length - 1);
        this.spiralTurns = theta / (2 * Math.PI);
        this.spiralLedCount = Math.floor(totalLength / (this.ledPitch / 1000)); // mm -> meters

        // Update info
        document.getElementById('spiralLength').textContent =
            `Spiral Length: ${this.spiralTotalLength.toFixed(2)} m (${(this.spiralTotalLength * 100).toFixed(1)} cm)`;
        document.getElementById('segmentCount').textContent =
            `Segments: ${this.spiralSegmentCount}`;
        document.getElementById('ledCount').textContent =
            `Total LEDs: ${this.spiralLedCount}`;
        document.getElementById('turnsCount').textContent =
            `Turns: ${this.spiralTurns.toFixed(1)}`;

        const ledsPerSeg = (this.segmentLength * 10) / this.ledPitch; // both effectively in mm
        document.getElementById('infoBox').textContent =
            `Tube diameter: ${this.tubeDiameter} mm\n` +
            `Spiral spacing: ${this.spiralSpacing} mm\n` +
            `Segment length: ${this.segmentLength} cm\n` +
            `LED pitch: ${this.ledPitch} mm\n` +
            `LEDs per segment: ${ledsPerSeg.toFixed(1)}\n` +
            `Wall: ${this.wallWidth} x ${this.wallHeight} m`;
    }

    // Compute normal (perpendicular to tangent) at curve point index i
    normalAt(i) {
        const pts = this.curvePoints;
        let dx, dy;
        if (i < pts.length - 1) {
            dx = pts[i + 1].x - pts[i].x;
            dy = pts[i + 1].y - pts[i].y;
        } else {
            dx = pts[i].x - pts[i - 1].x;
            dy = pts[i].y - pts[i - 1].y;
        }
        const len = Math.sqrt(dx * dx + dy * dy);
        if (len === 0) return { nx: 0, ny: 1 };
        return { nx: -dy / len, ny: dx / len };
    }

    draw() {
        const ctx = this.ctx;
        ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

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

        const step = 0.5;
        const extent = Math.max(this.wallWidth, this.wallHeight) / 2 + 0.5;
        for (let v = -extent; v <= extent; v += step) {
            const p1 = this.worldToCanvas(v, -extent);
            const p2 = this.worldToCanvas(v, extent);
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
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

        ctx.fillStyle = '#555';
        ctx.font = '11px -apple-system, sans-serif';
        ctx.fillText(`${this.wallWidth}m x ${this.wallHeight}m`, tl.x + 4, tl.y - 6);
        ctx.restore();
    }

    drawSpiral() {
        if (this.curvePoints.length < 2) return;
        const ctx = this.ctx;
        const tubeRadiusM = (this.tubeDiameter / 1000) / 2;

        ctx.save();

        // Build outer and inner edge points
        const outerPts = [];
        const innerPts = [];

        for (let i = 0; i < this.curvePoints.length; i++) {
            const p = this.curvePoints[i];
            const { nx, ny } = this.normalAt(i);
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

        // Outer edge line
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

        // Inner edge line
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

        // Draw segment boundary lines (perpendicular across tube at each segment joint)
        if (this.showSegments) {
            ctx.strokeStyle = 'rgba(255, 100, 50, 0.7)';
            ctx.lineWidth = 1.5;
            for (const idx of this.segmentIndices) {
                const po = this.worldToCanvas(outerPts[idx].x, outerPts[idx].y);
                const pi = this.worldToCanvas(innerPts[idx].x, innerPts[idx].y);
                ctx.beginPath();
                ctx.moveTo(po.x, po.y);
                ctx.lineTo(pi.x, pi.y);
                ctx.stroke();
            }
        }

        // Draw LEDs along the curve
        if (this.showLeds) {
            const ledPitchM = this.ledPitch / 1000; // mm -> meters
            let accumDist = 0;

            for (let i = 1; i < this.curvePoints.length; i++) {
                const prev = this.curvePoints[i - 1];
                const curr = this.curvePoints[i];
                const dx = curr.x - prev.x;
                const dy = curr.y - prev.y;
                const stepLen = Math.sqrt(dx * dx + dy * dy);
                if (stepLen === 0) continue;

                const ux = dx / stepLen;
                const uy = dy / stepLen;

                let d = ledPitchM - accumDist;
                while (d <= stepLen) {
                    const lx = prev.x + ux * d;
                    const ly = prev.y + uy * d;
                    const lp = this.worldToCanvas(lx, ly);
                    const ledSize = Math.max(1.5, this.worldScale(0.003));
                    ctx.beginPath();
                    ctx.arc(lp.x, lp.y, ledSize, 0, Math.PI * 2);
                    ctx.fillStyle = '#ffcc00';
                    ctx.fill();
                    ctx.strokeStyle = '#cc9900';
                    ctx.lineWidth = 0.5;
                    ctx.stroke();
                    d += ledPitchM;
                }
                accumDist = stepLen - (d - ledPitchM);
            }
        }

        // Center point
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

        // Sample every Nth curve point for hit-testing (curve is dense)
        const step = Math.max(1, Math.floor(this.curvePoints.length / 500));
        let minDist = Infinity;
        let closestIdx = -1;
        for (let i = 0; i < this.curvePoints.length; i += step) {
            const cp = this.worldToCanvas(this.curvePoints[i].x, this.curvePoints[i].y);
            const d = (cp.x - mx) ** 2 + (cp.y - my) ** 2;
            if (d < minDist) {
                minDist = d;
                closestIdx = i;
            }
        }
        minDist = Math.sqrt(minDist);

        if (minDist < 30 && closestIdx >= 0) {
            const p = this.curvePoints[closestIdx];
            // Figure out which segment this point belongs to
            let segNum = 0;
            for (let s = 0; s < this.segmentIndices.length - 1; s++) {
                if (closestIdx >= this.segmentIndices[s] && closestIdx < this.segmentIndices[s + 1]) {
                    segNum = s + 1;
                    break;
                }
            }
            // Cumulative length (approximate from index proportion)
            const frac = closestIdx / (this.curvePoints.length - 1);
            const cumLen = frac * this.spiralTotalLength;

            this.tooltip.style.display = 'block';
            this.tooltip.style.left = (e.clientX + 12) + 'px';
            this.tooltip.style.top = (e.clientY + 12) + 'px';
            this.tooltip.textContent =
                `Segment: ${segNum} / ${this.spiralSegmentCount}\n` +
                `Radius: ${(p.r * 100).toFixed(1)} cm\n` +
                `Length to here: ${cumLen.toFixed(2)} m\n` +
                `Angle: ${(p.theta * 180 / Math.PI).toFixed(1)}°`;
        } else {
            this.tooltip.style.display = 'none';
        }
    }
}

const app = new SpiralVisualizer();
